// What the master data screens show for each kind of record (UI-AD-04 and UI-AD-05): the table's columns and
// the form's fields. Field keys are the API's own names, because the rows and the form go back and forth as they are.

export type EntityKey =
  | "areas"
  | "routes"
  | "vehicles"
  | "permits"
  | "people"
  | "categories"
  | "severities"
  | "mediums";

/** One listed record. Besides these, it holds its fields and the names looked up for display (area_name, ...). */
export type Row = { id: number; is_active: boolean; [key: string]: unknown };

type Option = { value: string; label: string };

export type FieldDef = { key: string; label: string; required?: boolean } & (
  | { type: "text"; max: number; hint?: string }
  | { type: "textarea"; max: number }
  | { type: "select"; options: Option[] }
  // Another record. Short lists open as a drop-down; long ones are searched as you type.
  | { type: "record"; entity: EntityKey; shownAs: string; search: boolean }
);

export type Column = { label: string; value: (row: Row) => string | null };

export type Entity = {
  title: string;
  singular: string;
  blurb: string; // the line on the hub card
  rules: string[]; // what the administrator should know before editing
  columns: Column[]; // the first one is the record's name
  fields: FieldDef[];
  canAdd: boolean;
  canDeactivate: (row: Row) => boolean;
};

const text = (key: string) => (row: Row) => (row[key] == null ? null : String(row[key]));
const labelOf = (options: Option[], key: string) => (row: Row) =>
  options.find((o) => o.value === row[key])?.label ?? null;

const PLACE_KINDS = [
  { value: "route", label: "Route" },
  { value: "stand", label: "Stand" },
];
const VEHICLE_TYPES = [
  { value: "bus", label: "Bus" },
  { value: "trishaw", label: "Trishaw" },
];
export const PERSON_TYPES = [
  { value: "driver", label: "Driver" },
  { value: "conductor", label: "Conductor" },
  { value: "owner", label: "Owner" },
  { value: "sprpta_staff", label: "SPRPTA staff" },
];

const always = () => true;
const NEVER_DELETED = "Records are deactivated, never deleted, so the complaints that use them stay intact.";

export const ENTITIES: Record<EntityKey, Entity> = {
  areas: {
    title: "Areas",
    singular: "area",
    blurb: "Where complaints are forwarded",
    rules: [
      "A complaint goes to the Level 2 officer of its vehicle's registered area.",
      "An area with active vehicles or an active Level 2 officer cannot be deactivated.",
      NEVER_DELETED,
    ],
    columns: [{ label: "Name", value: text("name") }],
    fields: [{ key: "name", label: "Name", type: "text", max: 120, required: true }],
    canAdd: true,
    canDeactivate: always,
  },
  routes: {
    title: "Routes and stands",
    singular: "route or stand",
    blurb: "Bus routes and trishaw stands",
    rules: ["Permits point to a route. Level 1 sees only active routes and stands.", NEVER_DELETED],
    columns: [
      { label: "Name", value: text("name") },
      { label: "Kind", value: labelOf(PLACE_KINDS, "kind") },
      { label: "Area", value: text("area_name") },
    ],
    fields: [
      { key: "kind", label: "Kind", type: "select", options: PLACE_KINDS, required: true },
      { key: "name", label: "Name", type: "text", max: 120, required: true, hint: "For example 2 Galle - Matara" },
      { key: "area_id", label: "Area", type: "record", entity: "areas", shownAs: "area_name", search: false },
    ],
    canAdd: true,
    canDeactivate: always,
  },
  vehicles: {
    title: "Vehicles",
    singular: "vehicle",
    blurb: "Buses and trishaws, each with its area",
    rules: [
      "A vehicle must have a registered area, because forwarding depends on it.",
      "Numbers are matched ignoring spaces and dashes, so NA-1234 and NA 1234 are the same bus.",
      NEVER_DELETED,
    ],
    columns: [
      { label: "Vehicle number", value: text("vehicle_number") },
      { label: "Type", value: labelOf(VEHICLE_TYPES, "vehicle_type") },
      { label: "Registered area", value: text("area_name") },
      { label: "Owner", value: text("owner_name") },
    ],
    fields: [
      { key: "vehicle_number", label: "Vehicle number", type: "text", max: 30, required: true, hint: "For example NA-1234" },
      { key: "vehicle_type", label: "Type", type: "select", options: VEHICLE_TYPES, required: true },
      {
        key: "registered_area_id",
        label: "Registered area",
        type: "record",
        entity: "areas",
        shownAs: "area_name",
        search: false,
        required: true,
      },
      { key: "owner_person_id", label: "Owner", type: "record", entity: "people", shownAs: "owner_name", search: true },
    ],
    canAdd: true,
    canDeactivate: always,
  },
  permits: {
    title: "Permits",
    singular: "permit",
    blurb: "Route permits and their holders",
    rules: ["Each permit belongs to one vehicle. Level 1 fills the permit in from the vehicle.", NEVER_DELETED],
    columns: [
      { label: "Permit number", value: text("permit_number") },
      { label: "Vehicle", value: text("vehicle_number") },
      { label: "Route", value: text("route_name") },
      { label: "Holder", value: text("holder_name") },
    ],
    fields: [
      { key: "permit_number", label: "Permit number", type: "text", max: 30, required: true },
      {
        key: "vehicle_id",
        label: "Vehicle",
        type: "record",
        entity: "vehicles",
        shownAs: "vehicle_number",
        search: true,
        required: true,
      },
      { key: "route_stand_id", label: "Route", type: "record", entity: "routes", shownAs: "route_name", search: true },
      { key: "holder_person_id", label: "Holder", type: "record", entity: "people", shownAs: "holder_name", search: true },
    ],
    canAdd: true,
    canDeactivate: always,
  },
  people: {
    title: "People",
    singular: "person",
    blurb: "Drivers, conductors, owners and staff",
    rules: ["These are the people complaints can be about, and who receive ratings.", NEVER_DELETED],
    columns: [
      { label: "Name", value: text("full_name") },
      { label: "Type", value: labelOf(PERSON_TYPES, "person_type") },
      { label: "Staff number", value: text("staff_number") },
      { label: "Phone", value: text("phone") },
    ],
    fields: [
      { key: "full_name", label: "Full name", type: "text", max: 120, required: true },
      { key: "person_type", label: "Type", type: "select", options: PERSON_TYPES, required: true },
      { key: "staff_number", label: "Staff number", type: "text", max: 40, hint: "For SPRPTA staff" },
      { key: "phone", label: "Phone", type: "text", max: 40 },
    ],
    canAdd: true,
    canDeactivate: always,
  },
  categories: {
    title: "Categories",
    singular: "category",
    blurb: "What a complaint is about",
    rules: ["Level 1 picks one category for every complaint.", NEVER_DELETED],
    columns: [
      { label: "Name", value: text("name") },
      { label: "Description", value: text("description") },
    ],
    fields: [
      { key: "name", label: "Name", type: "text", max: 120, required: true },
      { key: "description", label: "Description", type: "textarea", max: 500 },
    ],
    canAdd: true,
    canDeactivate: always,
  },
  severities: {
    title: "Severities",
    singular: "severity",
    blurb: "Critical, High, Medium and Low",
    rules: [
      "The four severities are fixed: they can be renamed, not added or deactivated.",
      "Their time targets and rating weights are set under Settings.",
    ],
    columns: [
      { label: "Name", value: text("name") },
      { label: "Rank", value: (row) => `${row.rank}` },
    ],
    fields: [{ key: "name", label: "Name", type: "text", max: 120, required: true }],
    canAdd: false,
    canDeactivate: () => false,
  },
  mediums: {
    title: "Mediums",
    singular: "medium",
    blurb: "How a complaint reached SPRPTA",
    rules: ["Portal is used by the complainant portal, so it cannot be renamed or deactivated.", NEVER_DELETED],
    columns: [
      { label: "Name", value: text("name") },
      { label: "Used by", value: (row) => (row.is_system ? "Complainant portal" : "Level 1") },
    ],
    fields: [{ key: "name", label: "Name", type: "text", max: 120, required: true }],
    canAdd: true,
    canDeactivate: (row) => !row.is_system,
  },
};

export const ENTITY_KEYS = Object.keys(ENTITIES) as EntityKey[];

export function isEntityKey(value: string): value is EntityKey {
  return value in ENTITIES;
}

/** How a record is named in a picker, for example "NA-1234" or "Sunil Perera (Driver)". */
export function recordName(entity: EntityKey, row: Row): string {
  if (entity === "people") {
    const type = PERSON_TYPES.find((t) => t.value === row.person_type)?.label;
    return type ? `${row.full_name} (${type})` : String(row.full_name);
  }
  return String(ENTITIES[entity].columns[0].value(row) ?? row.id);
}
