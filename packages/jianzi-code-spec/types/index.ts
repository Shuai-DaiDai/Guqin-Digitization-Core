/* eslint-disable */
/**
 * Generated from schema/jianzi-v1.schema.json.
 * Update the schema first, then regenerate this file from the workspace script.
 */

export type ComponentSlot = string | null;

export type VisualLayout =
  | "single"
  | "top_bottom"
  | "left_right"
  | "top_middle_bottom"
  | "top_left_right_bottom"
  | "enclosing"
  | "surround"
  | "complex";

export type RightHandFinger =
  | "thumb"
  | "index"
  | "middle"
  | "ring"
  | "little"
  | "unknown";

export type LeftHandFinger = RightHandFinger | "none";

export type RightHandTechnique =
  | "gou"
  | "mo"
  | "tiao"
  | "ti"
  | "da"
  | "bo"
  | "fu"
  | "lun"
  | "pi"
  | "zhai"
  | `custom:${string}`;

export type LeftHandPitchVariation =
  | "none"
  | "yin"
  | "nao"
  | "chuo"
  | "zhu"
  | "jin"
  | "tui"
  | "fanqi"
  | `custom:${string}`;

export type LeftHandTimbreVariation =
  | "none"
  | "open_string"
  | "harmonic"
  | "stopped_string"
  | "vibrato"
  | "slide_resonance"
  | `custom:${string}`;

export type NoteType = "open" | "stopped" | "harmonic";

export type OrnamentToken =
  | "vibrato"
  | "slide_in"
  | "slide_out"
  | "grace_start"
  | "grace_continue"
  | "grace_end"
  | "slur_start"
  | "slur_continue"
  | "slur_end"
  | `custom:${string}`;

export type GuqinStringNumber = 1 | 2 | 3 | 4 | 5 | 6 | 7;

export type HuiNumber = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13;

export type NumberedDegree = 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7;

export type AccidentalShift = -1 | 0 | 1;

export type NotationSystem = "jianzipu" | "jianpu" | "musicxml" | "midi" | "nltabs";

export interface VisualComponents {
  top_left: ComponentSlot;
  top_right: ComponentSlot;
  bottom_inner: ComponentSlot;
  bottom_outer: ComponentSlot;
}

export interface VisualLayer {
  char_text: string;
  layout: VisualLayout;
  components: VisualComponents;
}

export interface Position {
  hui: HuiNumber | null;
  fraction: number | null;
}

export interface RightHandAction {
  finger: RightHandFinger;
  technique: RightHandTechnique;
}

export interface LeftHandAction {
  finger: LeftHandFinger;
  pitch_variation: LeftHandPitchVariation;
  timbre_variation: LeftHandTimbreVariation;
}

export interface PhysicalLayer {
  note_type: NoteType;
  string: GuqinStringNumber;
  position: Position;
  right_hand: RightHandAction;
  left_hand: LeftHandAction;
  ornaments?: OrnamentToken[];
}

export interface NumberedNotation {
  degree: NumberedDegree;
  accidental: AccidentalShift;
  octave_shift: number;
  harmonic_mark: boolean;
}

export interface AcousticLayer {
  pitch_name: string;
  midi_note: number;
  duration_beats: number;
  musicxml_snippet: string;
  numbered_notation?: NumberedNotation;
}

export interface JianziNoteEvent {
  id: string;
  visual: VisualLayer;
  physical: PhysicalLayer;
  acoustic: AcousticLayer;
}

export type JianziV1 = JianziNoteEvent;

export interface GuqinTuning {
  label: string;
  strings: [string, string, string, string, string, string, string];
}

export interface PieceSource {
  edition: string;
  original_source?: string;
  performer?: string;
  transcriber?: string;
  reference_repository?: string;
}

export interface PieceMetadata {
  title: string;
  subtitle?: string;
  notation_systems: NotationSystem[];
  tuning: GuqinTuning;
  source: PieceSource;
}

export interface TimeSignature {
  numerator: number;
  denominator: 1 | 2 | 4 | 8 | 16 | 32;
}

export interface JianziMeasure {
  index: number;
  time_signature?: TimeSignature;
  events: JianziNoteEvent[];
}

export interface JianziSection {
  id: string;
  label?: string;
  measures: JianziMeasure[];
}

export interface JianziDocumentV1 {
  schema_version: "jianzi-document-v1";
  piece: PieceMetadata;
  sections: JianziSection[];
}
