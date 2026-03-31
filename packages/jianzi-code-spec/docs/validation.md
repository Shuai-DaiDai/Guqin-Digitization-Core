# Validation

This script checks the example JSON files in `packages/jianzi-code-spec/examples` against the schemas in `packages/jianzi-code-spec/schema`.

## Run

From the repo root:

```bash
node packages/jianzi-code-spec/scripts/validate.cjs
```

## What it checks

- Required fields
- Object and array shapes
- String patterns and lengths
- Numeric bounds
- Enums and constant values
- `anyOf`, `allOf`, `if`/`then`
- Local schema references between files
- The current example file against the document schema

## Notes

- The script is pure Node and does not require an installed npm dependency.
- If the spec grows to use more of JSON Schema in future, the next step would be to switch this to a full validator such as `ajv`, but that is not required for the current schemas.
