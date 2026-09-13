from pathlib import Path
import subprocess

path = Path(".agents/skills/verify-spec/SKILL.md")
text = path.read_text()

block = """#### Child-Owned Execution Requirement\n\nA required delegated gate is **not invoked** merely because the parent reads the child `SKILL.md` and runs commands that resemble its procedure. The owning skill must execute as an actual child/nested skill operation and must return its own current terminal result.\n\nUse either a distinct child context or a native nested-skill mechanism that preserves the complete owner-skill contract. Execute mutation-capable delegated gates sequentially when they share the same worktree. The parent may prepare inputs and consume returned evidence, but it may not substitute its own abbreviated implementation of the child gate.\n\nA direct parent command may provide supporting evidence, but it cannot satisfy the delegated gate unless the owner skill itself explicitly defines that command output as its terminal result and the owner skill invocation returns that result.\n\nBefore finalization require:\n\n```text\nRequired delegated gates: <n>\nOwner-skill invocations completed: <n>\nValid owner terminal results captured: <n>\nParent-substituted delegated gates: 0\nRequired delegated gates without owner terminal result: 0\n```\n\nIf a required child skill was only read, paraphrased, or manually emulated by the parent, classify that delegated gate `unresolved` and block PASS.\n\n"""

count = text.count(block)
if count != 1:
    raise SystemExit(f"expected exactly one delegated subagent block, found {count}")

text = text.replace(block, "", 1)
path.write_text(text)

subprocess.run(["git", "diff", "--check", "--", str(path)], check=True)
subprocess.run(["git", "add", str(path)], check=True)
subprocess.run(["git", "diff", "--cached", "--check"], check=True)
subprocess.run(["git", "config", "user.name", "Bob Taylor"], check=True)
subprocess.run(["git", "config", "user.email", "bobltaylorjr@gmail.com"], check=True)
subprocess.run(["git", "commit", "-m", "fix(skills): revert delegated subagent requirement"], check=True)
subprocess.run(["git", "push", "origin", "HEAD:main"], check=True)
