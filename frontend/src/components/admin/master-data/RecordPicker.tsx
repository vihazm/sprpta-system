"use client";

import { useEffect, useState } from "react";
import { iconButton, inputClass } from "@/components/dashboard/controls";
import { Icon } from "@/components/dashboard/icons";
import { loadRecords } from "./api";
import { recordName, type FieldDef, type Row } from "./entities";

type RecordField = Extract<FieldDef, { type: "record" }>;

type Props = {
  id: string;
  field: RecordField;
  value: number | null;
  label: string | null; // the name of the chosen record
  onChange: (value: number | null, label: string | null) => void;
};

/** Chooses another record, for example a vehicle's area or owner. Only active records can be chosen. */
export function RecordPicker(props: Props) {
  return props.field.search ? <SearchPicker {...props} /> : <DropDown {...props} />;
}

// For short lists such as the areas: all of them in a drop-down.
function DropDown({ id, field, value, label, onChange }: Props) {
  const [options, setOptions] = useState<Row[]>([]);

  useEffect(() => {
    let current = true;
    void loadRecords(field.entity, { status: "active", pageSize: 100 }).then((result) => {
      if (current && result.ok) setOptions(result.data.items);
    });
    return () => {
      current = false;
    };
  }, [field.entity]);

  const chosenIsListed = value === null || options.some((o) => o.id === value);
  return (
    <select
      id={id}
      className={inputClass}
      value={value ?? ""}
      onChange={(e) => {
        const chosen = options.find((o) => o.id === Number(e.target.value));
        onChange(chosen ? chosen.id : null, chosen ? recordName(field.entity, chosen) : null);
      }}
    >
      <option value="">{field.required ? "Choose…" : "None"}</option>
      {!chosenIsListed && <option value={value}>{label} (inactive)</option>}
      {options.map((o) => (
        <option key={o.id} value={o.id}>
          {recordName(field.entity, o)}
        </option>
      ))}
    </select>
  );
}

// For long lists such as people and vehicles: type to search, then pick one of the first matches.
function SearchPicker({ id, field, value, label, onChange }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Row[] | null>(null);

  useEffect(() => {
    const term = query.trim();
    if (!term) return;
    let current = true;
    const timer = setTimeout(() => {
      void loadRecords(field.entity, { search: term, status: "active" }).then((result) => {
        if (current) setResults(result.ok ? result.data.items : []);
      });
    }, 250);
    return () => {
      current = false;
      clearTimeout(timer);
    };
  }, [query, field.entity]);

  if (value !== null) {
    return (
      <div className="flex items-center gap-2 rounded-[0.9rem] bg-field px-[0.9rem] py-[0.35rem]">
        <span id={id} className="min-w-0 flex-1 truncate text-[0.88rem] font-medium">
          {label ?? `#${value}`}
        </span>
        <button type="button" className={iconButton} aria-label={`Clear ${field.label.toLowerCase()}`} onClick={() => onChange(null, null)}>
          <Icon name="close" size={13} />
        </button>
      </div>
    );
  }

  const note = results === null ? "Searching…" : results.length === 0 ? "No active match." : null;
  return (
    <div className="flex flex-col gap-1.5">
      <input
        id={id}
        type="search"
        className={inputClass}
        placeholder={`Search ${field.label.toLowerCase()}…`}
        value={query}
        autoComplete="off"
        onChange={(e) => {
          setQuery(e.target.value);
          setResults(null);
        }}
      />
      {query.trim() && (
        <ul className="m-0 flex max-h-[14rem] list-none flex-col overflow-y-auto rounded-[0.9rem] border-[1.5px] border-[#E5E7EB] bg-white p-1">
          {note && <li className="px-3 py-2 text-[0.8rem] text-muted">{note}</li>}
          {results?.map((row) => (
            <li key={row.id}>
              <button
                type="button"
                onClick={() => {
                  onChange(row.id, recordName(field.entity, row));
                  setQuery("");
                }}
                className="focus-ring w-full cursor-pointer rounded-[0.7rem] px-3 py-2 text-left text-[0.8rem] font-semibold hover:bg-[#fbf5f6]"
              >
                {recordName(field.entity, row)}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
