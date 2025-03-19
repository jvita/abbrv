name: Upload new system
description: Upload a system that was exported by abbrv
title: "[SYSTEM-UPLOAD]: "
labels: ["system-upload"]
projects: ["octo-org/1", "octo-org/44"]
assignees:
  - octocat
body:
  - type: markdown
    attributes:
      value: |
        Thanks for taking the time to fill out this bug report!
  - type: input
    id: name
    attributes:
      label: Your Name
  - type: textarea
    id: description
      label: System description
