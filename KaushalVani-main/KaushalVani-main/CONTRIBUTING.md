# Contributing to KaushalVani

Thank you for your interest in contributing to KaushalVani!

## Development Guidelines
1. Follow existing TypeScript and Python coding conventions.
2. Ensure no hardcoded government data; query authoritative NQR/NSQF sources.
3. Write clean, readable code with standard JSDoc / docstring comments.
4. Maintain accessibility standards (UX4G / GIGW compliance).

## Pull Request Process
1. Fork the repository and create a feature branch.
2. Ensure `npm run build` succeeds in both `/frontend` and `/backend`.
3. Run `node scripts/test-scenarios.js` to pass all integration test cases.
4. Open a pull request with a descriptive summary of your changes.
