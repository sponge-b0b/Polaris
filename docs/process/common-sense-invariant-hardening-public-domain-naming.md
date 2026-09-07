# Public Domain Naming Attention

Exported domain/public names are part of the contract readers and downstream code consume.

When an exported type uses a generic noun such as `Fact`, `Record`, `Data`, `Metadata`, `State`, `Context`, `Manager`, `Reference`, or similar language, apply the repository Proactive Attention Duty and ask whether the name remains understandable at its import/use site without hidden file-local or conversational context.

If the owning bounded context, domain concept, lifecycle role, authority role, or historical meaning is necessary to understand the type, qualify the name with the shortest wording that preserves that material distinction. Do not add verbosity when existing public context already makes the meaning unambiguous.

A naming concern is Attention, not mutation authority. If the public name is already fixed by authoritative design, follow that design. If competing names imply materially different domain meaning or downstream contract, surface the design gap rather than selecting one during implementation.
