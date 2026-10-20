import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => cleanup());

// Some browsers return a value even though the DOM type declares `void`.
// Effects must never forward that value to React as an effect cleanup callback.
Element.prototype.scrollIntoView = (() => ({})) as typeof Element.prototype.scrollIntoView;

// Existing interaction tests use the accessibility path so they do not wait
// through demo pacing. Timeline tests opt into normal motion explicitly.
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: query === "(prefers-reduced-motion: reduce)",
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});
