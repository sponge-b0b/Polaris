# Python Coding Standards

This document establishes the official coding standards for this project. All code added to this repository must adhere to these guidelines to ensure consistency, readability, and type safety. 

Compliance is enforced automatically during CI/CD pipelines via **Ruff** and **Mypy**.

---

## 🎯 Scope
> ⚠️ **Scope Exclusion**: Markdown documents (`*.md`), configuration files, and documentation assets are exempt from these guidelines. These rules apply strictly to Python (`*.py`) source files.

## 🚀 Automated Quality Controls

Before submitting a Pull Request, you must run the local verification suite. Code that fails these checks will be blocked from merging.

### 1. Linting & Formatting (Ruff)
We use `ruff` to manage code style (replacing Flake8, Black, isort, and bandit).
```bash
# Check for lint errors and auto-fixable issues
ruff check --glob "*.py" --fix

# Format the codebase
ruff format --glob "*.py"
```

### 2. Static Type Checking (Mypy)
We enforce strict, static type hints to eliminate runtime type errors.
```bash
# Verify type consistency
mypy . --glob "*.py"
```

---

## 🎨 Code Style & Layout (Ruff Compliance)

Our code style is governed by PEP 8 and enforced by Ruff's formatter.

* **Indentation**: Use exactly **4 spaces** per indentation level. Do not use tabs.
* **Line Length**: Max line length is **88 characters** (matching default Ruff/Black settings).
* **Quotes**: Prefer **double quotes (`"`)** for all strings unless single quotes avoid escaping.
* **Imports Ordering**: Group and alphabetize imports automatically using Ruff. 
  1. Standard library imports
  2. Third-party library imports
  3. Local/application imports
* **Trailing Commas**: Use trailing commas in multi-line lists, dictionaries, and function arguments to minimize git diffs.

---

## 🏷️ Typing & Type Hints (Mypy Compliance)

Every public function, method, and module component must be explicitly typed. 

### 1. Function Signatures
Always provide explicit types for all inputs and the return value, even if it returns `None`.
```python
# ❌ Bad
def calculate_total(price, tax):
    return price + (price * tax)

#  Good
def calculate_total(price: float, tax: float) -> float:
    return price + (price * tax)
```

### 2. Handling Optional Values
If a variable or argument can accept `None`, you must declare it using Python 3.10+ union pipes (`|`). Do not rely on implicit optional types.
```python
# ❌ Bad
def find_user(user_id: int) -> User: ...  # Will crash if user isn't found

#  Good
def find_user(user_id: int) -> User | None: ...
```

### 3. Collection Sizing
Use standard collection classes (`list`, `dict`, `set`) instead of the deprecated `typing.List` or `typing.Dict`.
```python
# ❌ Bad (Legacy)
from typing import List, Dict
def process_data(items: List[str]) -> Dict[str, int]: ...

#  Good (Modern Python 3.10+)
def process_data(items: list[str]) -> dict[str, int]: ...
```

### 4. Bypassing Type Checks
* Avoid using `Any` wherever possible. Opt for `Protocol` or generic TypeVars (`TypeVar`) instead.
* If a third-party package lacks types, use `# type: ignore` as a last resort, always specifying the exact error code:
  ```python
  import untyped_library  # type: ignore[import-untyped]
  ```

---

## 🐍 Pythonic Best Practices

### 1. Explicit variable naming
* **`snake_case`**: Variables, functions, methods, modules, and packages.
* **`PascalCase`**: Classes, Exceptions, and TypeVars.
* **`UPPER_SNAKE_CASE`**: Constants defined at the module level.

### 2. Error & Exception Handling
* Never catch a generic, naked `Exception`. Always target specific exceptions.
* Never use `pass` in an exception block without an explanatory comment.

```python
# ❌ Bad
try:
    data = fetch_api()
except Exception:
    pass

#  Good
try:
    data = fetch_api()
except ConnectionError as err:
    logger.error("API connection failed: %s", err)
    data = {}
```

### 3. Resource Management
Always use context managers (`with` statements) when opening files, database sockets, or network streams to guarantee proper cleanup.

```python
#  Good
with open("config.json", "r", encoding="utf-8") as file:
    config = json.load(file)
```

---
