---
name: basic
description: 囊泡建模阶段的顶层技能规范。仅用于 VEVs 仓库中 vesicle 目录相关任务。触发后只读取 VEVs/vesicle 。涉及参数写入、外部资源引用或受规范影响的代码改动前，必须先联网核对官方权威来源并注明依据。代码需包含详细中文注释。改动完成后先询问用户是否需要飞书总结，仅在用户确认并指定阶段范围后再生成。
---

# Basic Skill

## 1. Scope
- Use this skill only for tasks under `VEVs/vesicle`.

## 2. Mandatory Source Verification
- Before landing code, always verify official sources for:
- scientific parameters,
- external references,
- format/spec-dependent logic (Martini/GROMACS conventions).
- Prefer official Martini docs/repos (including `insane.py`) and official GROMACS docs.
- In responses, explicitly map decisions to source URLs and distinguish direct conclusions vs engineering inferences.

## 3. Code Commenting
- Write detailed Chinese comments for:
- core algorithm logic,
- key fields/units/ranges,
- naming semantics,
- error-branch intent.

## 4. Feishu Summary Policy
- After code changes, ask first: whether user needs a Feishu summary.
- Generate summary only if user confirms and specifies summary scope (stages/time/file range).

## 5. Invocation Policy
- This skill is configured for explicit invocation only (`allow_implicit_invocation: false`).
- Recommend user explicitly writes `$basic` when working on vesicle modeling tasks.
