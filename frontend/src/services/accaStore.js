// Bet-slip store for the accumulator builder, persisted to localStorage so a slip
// survives navigation and reloads (same pattern the app uses for history/preferences).
//
// A selection: { id, label, fixture, prob, odds?, leagueId?, fixtureId? }

import { writable } from "svelte/store";

const KEY = "fixturecast_acca_slip";
const MAX_LEGS = 12;

function load() {
  try {
    if (typeof localStorage === "undefined") return [];
    const raw = localStorage.getItem(KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function persist(value) {
  try {
    if (typeof localStorage !== "undefined") {
      localStorage.setItem(KEY, JSON.stringify(value));
    }
  } catch {
    /* ignore quota / disabled storage */
  }
}

export const accaSlip = writable(load());
accaSlip.subscribe(persist);

export function addSelection(sel) {
  if (!sel || !sel.id) return;
  accaSlip.update((list) => {
    if (list.some((s) => s.id === sel.id)) return list; // dedupe
    if (list.length >= MAX_LEGS) return list; // sane cap
    return [...list, sel];
  });
}

export function removeSelection(id) {
  accaSlip.update((list) => list.filter((s) => s.id !== id));
}

export function clearSlip() {
  accaSlip.set([]);
}

export function isInSlip(list, id) {
  return Array.isArray(list) && list.some((s) => s.id === id);
}
