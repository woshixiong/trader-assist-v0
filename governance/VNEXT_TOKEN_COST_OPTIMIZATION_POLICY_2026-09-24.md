# VNext Token Cost Optimization Policy

## Purpose

Define how the engineering workflow preserves quality while minimizing model token consumption.

## Principles

- Use deterministic tools before model reasoning.
- Use the smallest capable model for each task.
- Reserve highest reasoning capability for architecture, final review, and unresolved decisions.
- Avoid repeated context transfer through structured artifacts.

## Routing

Mechanical tasks:
- deterministic tools / CI / scripts

Small semantic tasks:
- lightweight model execution

Large coherent coding tasks:
- Codex package workflow

High consequence decisions:
- Engineering Control

## Context Management

- GitHub artifacts are the durable state layer.
- Do not copy large transcripts between agents.
- Resume from checkpoints after interruption.

## Human Cost Boundary

Human participation remains concentrated at:
- initial planning and scope decisions;
- final protected actions.
