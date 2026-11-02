DOCUMENTATION TOOLING
audit_project.py: Python3 + Pillow. Read-only Unity source/level/asset inventory.
build_handbook.py: Python3 standard library. Rebuilds current Markdown and HTML from its embedded source. Original PDFs are separate inputs.
build_monetization_model.mjs: Node + @oai/artifact-tool. Optional authoring source; requires that package in your environment. Set HOTR_MODEL_OUTPUT to choose an output directory. The delivered XLSX can be edited normally in Excel without this tool.
package_handoff.py: Python3. --baseline <original M67R4 ZIP>. Adds current docs and verifies baseline bytes. Not a Unity build pipeline.
These tools are for handoff reproduction, not dependencies of the mobile game. No SDK credentials are included.
