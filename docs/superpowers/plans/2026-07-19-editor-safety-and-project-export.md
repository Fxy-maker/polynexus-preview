# Editor Safety and Self-Contained Project Export Implementation Plan

## Task 1: Define failing close-protection tests

- [x] Test clean close, Discard, Cancel, successful Save, and failed Save.
- [x] Run the tests red before changing `ChartEditor`.

## Task 2: Define failing project-package tests

- [x] Test package contents, relocated source paths, duplicate destination
      refusal, missing-source cleanup, and checksum manifest.
- [x] Run the tests red before implementing the service.

## Task 3: Implement core project package service

- [x] Add a pure service with safe source resolution, inline CSV support,
      checksums, and atomic zip replacement.
- [x] Keep document source paths bundle-relative and preserve figure assets.

## Task 4: Integrate ChartEditor

- [x] Add close decision handling and a project-package action using the
      existing QFileDialog boundary.
- [x] Keep save failures dirty and leave the editor open.

## Task 5: Verify and checkpoint

- [x] Run the task-scoped verifier and focused tests.
- [x] Update active memory and create one `auto_commit.py` checkpoint.
