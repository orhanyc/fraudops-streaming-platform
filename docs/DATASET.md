# Synthetic Dataset Card

## Purpose

The generator creates reproducible payment events for engineering demonstrations, model evaluation and drift testing. It contains no real people, bank customers, accounts or employer information.

## Generation process

Each synthetic account has a home country, a primary device and a typical payment amount. Events progress through simulated time with benign variation in amount, channel, device and counterparty age. A small labeled subset receives one of three independently designed scenarios:

- `account_takeover`: a new device, a foreign country and an unusually large payment
- `velocity_burst`: closely spaced payments with elevated amounts
- `new_counterparty`: a new counterparty relationship and an elevated payment

The generator also produces benign new-device, international and high-amount events so that no single field perfectly identifies the label.

## Splitting and leakage controls

Rows are sorted by simulated time and divided into train, validation and test partitions. Online features use only earlier events for an account. The current label and future outcomes are never included in model features.

## Limitations

Synthetic scenarios are simpler than real financial behavior and must not be interpreted as an estimate of production fraud prevalence or detection quality. Performance numbers describe this repository's generated benchmark only.

## License and provenance

The generator and resulting synthetic records are original code released under the repository MIT license. No external dataset is required.

