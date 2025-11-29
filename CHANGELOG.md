# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.3.0]

### Added
- Database migration management
- Better observability with automatic collection and centralized logging

### Changed
- Refactored setting module to add setting fields and support loading field values from multiple sources
- Renamed `scheme` module to `model` and fixed various design issues
- Enhanced integration of event-driven patterns
- Improved overall developer experience
- Removed internal support of Supabase Auth
- Removed built-in auth/session module (`blue_firmament.auth`) and JWT utilities. DAL now accepts an optional generic mapping for token/session data instead of `AuthSession`.
