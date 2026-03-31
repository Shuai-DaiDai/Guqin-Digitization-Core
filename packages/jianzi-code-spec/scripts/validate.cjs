#!/usr/bin/env node

const fs = require('node:fs');
const path = require('node:path');

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function isObject(value) {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function resolvePointer(root, pointer) {
  if (!pointer || pointer === '#') return root;
  const fragments = pointer.startsWith('#/') ? pointer.slice(2).split('/') : pointer.split('/');
  let current = root;
  for (const fragment of fragments) {
    const key = fragment.replace(/~1/g, '/').replace(/~0/g, '~');
    if (!isObject(current) && !Array.isArray(current)) {
      throw new Error(`Cannot resolve pointer ${pointer}`);
    }
    current = current[key];
  }
  return current;
}

function resolveSchemaRef(ref, schema, schemaDir) {
  if (ref.startsWith('#')) {
    return resolvePointer(schema, ref);
  }
  const [filePart, fragmentPart] = ref.split('#');
  const targetFile = path.resolve(schemaDir, filePart);
  const targetSchema = readJson(targetFile);
  if (!fragmentPart) return targetSchema;
  return resolvePointer(targetSchema, `#${fragmentPart}`);
}

function formatPath(pathParts) {
  if (!pathParts.length) return '<root>';
  return pathParts
    .map((part) => (typeof part === 'number' ? `[${part}]` : `.${part}`))
    .join('')
    .replace(/^\./, '');
}

function pushError(errors, pathParts, message) {
  errors.push(`${formatPath(pathParts)}: ${message}`);
}

function validateFormat(value, format) {
  if (format === 'uri') {
    try {
      new URL(value);
      return true;
    } catch {
      return false;
    }
  }
  return true;
}

function validateSchema(value, schema, ctx) {
  const errors = [];
  validateNode(value, schema, ctx, [], errors);
  return errors;
}

function validateNode(value, schema, ctx, pathParts, errors) {
  if (!schema) {
    pushError(errors, pathParts, 'schema resolution failed');
    return;
  }

  if (schema.$ref) {
    const targetFile = schema.$ref.startsWith('#')
      ? null
      : path.resolve(ctx.schemaDir, schema.$ref.split('#')[0]);
    const resolved = resolveSchemaRef(schema.$ref, ctx.rootSchema, ctx.schemaDir);
    const nextCtx = targetFile
      ? {
          rootSchema: resolved,
          schemaDir: path.dirname(targetFile),
        }
      : ctx;
    validateNode(value, resolved, nextCtx, pathParts, errors);
    return;
  }

  if (schema.allOf) {
    for (const subSchema of schema.allOf) {
      validateNode(value, subSchema, ctx, pathParts, errors);
    }
  }

  if (schema.anyOf) {
    let matched = false;
    for (const subSchema of schema.anyOf) {
      const candidateErrors = [];
      validateNode(value, subSchema, ctx, pathParts, candidateErrors);
      if (candidateErrors.length === 0) {
        matched = true;
        break;
      }
    }
    if (!matched) {
      pushError(errors, pathParts, 'must match at least one anyOf branch');
    }
    return;
  }

  if (schema.if) {
    const ifErrors = [];
    validateNode(value, schema.if, ctx, pathParts, ifErrors);
    if (ifErrors.length === 0) {
      if (schema.then) validateNode(value, schema.then, ctx, pathParts, errors);
    } else if (schema.else) {
      validateNode(value, schema.else, ctx, pathParts, errors);
    }
  }

  if (schema.const !== undefined && value !== schema.const) {
    pushError(errors, pathParts, `must equal constant ${JSON.stringify(schema.const)}`);
    return;
  }

  if (schema.enum && !schema.enum.includes(value)) {
    pushError(errors, pathParts, `must be one of ${schema.enum.map((v) => JSON.stringify(v)).join(', ')}`);
    return;
  }

  if (schema.type) {
    const types = Array.isArray(schema.type) ? schema.type : [schema.type];
    const matchesType = types.some((type) => {
      if (type === 'null') return value === null;
      if (type === 'array') return Array.isArray(value);
      if (type === 'object') return isObject(value);
      if (type === 'string') return typeof value === 'string';
      if (type === 'integer') return Number.isInteger(value);
      if (type === 'number') return typeof value === 'number' && Number.isFinite(value);
      if (type === 'boolean') return typeof value === 'boolean';
      return false;
    });
    if (!matchesType) {
      pushError(errors, pathParts, `must be of type ${types.join(' or ')}`);
      return;
    }
  }

  if (typeof value === 'string') {
    if (schema.minLength !== undefined && value.length < schema.minLength) {
      pushError(errors, pathParts, `must have length at least ${schema.minLength}`);
    }
    if (schema.maxLength !== undefined && value.length > schema.maxLength) {
      pushError(errors, pathParts, `must have length at most ${schema.maxLength}`);
    }
    if (schema.pattern) {
      const pattern = new RegExp(schema.pattern);
      if (!pattern.test(value)) {
        pushError(errors, pathParts, `must match pattern ${schema.pattern}`);
      }
    }
    if (schema.format && !validateFormat(value, schema.format)) {
      pushError(errors, pathParts, `must match format ${schema.format}`);
    }
  }

  if (typeof value === 'number') {
    if (schema.minimum !== undefined && value < schema.minimum) {
      pushError(errors, pathParts, `must be >= ${schema.minimum}`);
    }
    if (schema.maximum !== undefined && value > schema.maximum) {
      pushError(errors, pathParts, `must be <= ${schema.maximum}`);
    }
    if (schema.exclusiveMinimum !== undefined && value <= schema.exclusiveMinimum) {
      pushError(errors, pathParts, `must be > ${schema.exclusiveMinimum}`);
    }
    if (schema.exclusiveMaximum !== undefined && value >= schema.exclusiveMaximum) {
      pushError(errors, pathParts, `must be < ${schema.exclusiveMaximum}`);
    }
  }

  if (Array.isArray(value)) {
    if (schema.minItems !== undefined && value.length < schema.minItems) {
      pushError(errors, pathParts, `must have at least ${schema.minItems} items`);
    }
    if (schema.maxItems !== undefined && value.length > schema.maxItems) {
      pushError(errors, pathParts, `must have at most ${schema.maxItems} items`);
    }
    if (schema.uniqueItems) {
      const seen = new Set();
      for (let i = 0; i < value.length; i += 1) {
        const key = JSON.stringify(value[i]);
        if (seen.has(key)) {
          pushError(errors, pathParts, 'items must be unique');
          break;
        }
        seen.add(key);
      }
    }
    if (schema.items) {
      for (let i = 0; i < value.length; i += 1) {
        validateNode(value[i], schema.items, ctx, [...pathParts, i], errors);
      }
    }
  }

  if (isObject(value)) {
    if (schema.required) {
      for (const key of schema.required) {
        if (!(key in value)) {
          pushError(errors, pathParts, `missing required property ${JSON.stringify(key)}`);
        }
      }
    }

    if (schema.properties) {
      for (const [key, propSchema] of Object.entries(schema.properties)) {
        if (key in value) {
          validateNode(value[key], propSchema, ctx, [...pathParts, key], errors);
        }
      }
    }

    if (schema.additionalProperties === false && schema.properties) {
      const knownKeys = new Set(Object.keys(schema.properties));
      for (const key of Object.keys(value)) {
        if (!knownKeys.has(key)) {
          pushError(errors, pathParts, `unexpected property ${JSON.stringify(key)}`);
        }
      }
    }
  }
}

function validateAll() {
  const repoRoot = path.resolve(__dirname, '../../..');
  const specDir = path.join(repoRoot, 'packages/jianzi-code-spec');
  const schemaDir = path.join(specDir, 'schema');
  const examplesDir = path.join(specDir, 'examples');
  const schemaFiles = [
    path.join(schemaDir, 'jianzi-v1.schema.json'),
    path.join(schemaDir, 'jianzi-document-v1.schema.json'),
  ];
  const exampleFiles = fs.readdirSync(examplesDir)
    .filter((name) => name.endsWith('.json'))
    .map((name) => path.join(examplesDir, name));

  const schemas = new Map();
  for (const schemaFile of schemaFiles) {
    schemas.set(schemaFile, readJson(schemaFile));
  }

  const problems = [];

  for (const schemaFile of schemaFiles) {
    try {
      readJson(schemaFile);
    } catch (error) {
      problems.push(`schema parse failed: ${schemaFile}: ${error.message}`);
    }
  }

  for (const filePath of exampleFiles) {
    const data = readJson(filePath);
    const schemaFile = data && data.schema_version === 'jianzi-document-v1'
      ? path.join(schemaDir, 'jianzi-document-v1.schema.json')
      : path.join(schemaDir, 'jianzi-v1.schema.json');
    const schema = schemas.get(schemaFile);
    const errors = validateSchema(data, schema, {
      rootSchema: schema,
      schemaDir,
    });
    if (errors.length > 0) {
      problems.push(`${path.basename(filePath)}:\n  - ${errors.join('\n  - ')}`);
    } else {
      console.log(`OK ${path.relative(repoRoot, filePath)} -> ${path.relative(repoRoot, schemaFile)}`);
    }
  }

  if (problems.length > 0) {
    console.error('Validation failed.');
    for (const problem of problems) {
      console.error(problem);
    }
    process.exitCode = 1;
    return;
  }

  console.log(`Validated ${exampleFiles.length} example file(s) successfully.`);
}

validateAll();
