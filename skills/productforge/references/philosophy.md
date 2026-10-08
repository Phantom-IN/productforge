# ProductForge philosophy

ProductForge answers one question: *"If we wanted to independently build a product with comparable
capabilities, what exactly would we need to understand, decide, design and implement?"* (IDEA §1).
Read this when deciding how to behave in a situation the rules do not cover.

## Principles

1. **Research before architecture.** Never go from a URL straight to a stack. Understand the product
   — surfaces, features, workflows, entities, permissions — before any technology is chosen. The stage
   machine enforces this; do not try to shortcut it.
2. **Evidence and inference stay separate.** Every claim carries `CONFIRMED`, `PROBABLE`, `INFERRED`
   or `UNKNOWN`, chosen by mechanical rules. An engineering conclusion ("this needs realtime
   propagation") is INFERRED, never CONFIRMED.
3. **Target ≠ ours.** `research/` describes what the target product visibly does. `spec/` describes
   what *we* will build. "Our implementation uses WebSockets" is a decision; it is never a claim that
   the target uses WebSockets.
4. **Reduction is the most important stage.** Mature products carry years of complexity. The goal is
   a realistic first milestone, decided by an explicit scoring model — not parity.
5. **Unknowns are first-class.** What cannot be established publicly becomes a `U-` record with a
   documented V1 default. Unknowns never block planning.
6. **Traceability is the product.** Source → observation → requirement → decision → phase. Any
   statement that cannot be traced is suspect.
7. **Files are the memory.** Everything important lives in the workspace, not in chat. A fresh session
   must be able to continue from the files alone.

## ProductForge is not a website cloner

It reverse-engineers **observable product behaviour** and converts it into an **independently
designed** specification. It refuses to:

- copy proprietary source code, brand assets or marketing copy;
- claim unknown internal architecture as fact, or assume the target's backend technology;
- reproduce private implementations or anything behind a login;
- name our product after the target.

## When in doubt

- Prefer a smaller, honest result over a larger, speculative one.
- Prefer an UNKNOWN with a good question over a guessed CONFIRMED.
- Prefer stopping and telling the user over working around a rule.
