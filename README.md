# TestForge

A project-agnostic, multi-agent AI testing system that generates comprehensive Playwright test suites following ADSE testing standards.

## Overview

TestForge uses a team of AI agents (powered by CrewAI + GitHub Models) to:

1. **Read** your repository structure and understand the codebase
2. **Discover** API endpoints (via MCP server or Swagger/OpenAPI specs)
3. **Plan** a comprehensive test strategy with prioritized test cases
4. **Write** tests across three layers: Backend API, Frontend UI, End-to-End journeys
5. **Review** generated tests by running them and providing fix feedback
6. **Iterate** until tests compile and pass (up to 3 retry cycles)

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for Playwright)
- A GitHub Token with Models API access

### Installation

```bash
pip install -e .
```

### Configuration

1. Copy `.env.example` to `.env` and set your `GITHUB_TOKEN`
2. Copy `credentials.example.json` and fill in test account details

### Usage

```bash
# Basic usage
testforge --repo ./path/to/project --url https://app.example.com --creds credentials.json

# With MCP server config
testforge --repo ./path/to/project --url https://app.example.com --creds credentials.json --mcp-config mcp.json

# Custom output directory
testforge --repo ./project --url https://app.example.com --creds creds.json --output ./my-tests
```

### CLI Options

| Option | Description |
|--------|-------------|
| `--repo` | Path to the target repository (required) |
| `--url` | Application URL for testing (required) |
| `--creds` | Path to credentials JSON file (required) |
| `--output` | Output directory for generated tests (default: `./testforge-output`) |
| `--mcp-config` | Path to MCP server configuration (optional) |
| `--force` | Overwrite existing output directory |

## Output Structure (6-Layer Architecture)

```
testforge-output/
├── playwright.config.ts
├── package.json
├── tsconfig.json
├── core/
│   ├── types/enums.ts
│   └── constants/app.constants.ts
├── data/
│   └── credentials/accounts.ts
├── fixtures/
│   └── auth.fixture.ts
├── ui/
│   └── models/          # Page Object Models
├── tests/
│   ├── api/             # Backend API tests
│   ├── ui/              # Frontend UI tests
│   └── e2e/             # End-to-end journey tests
└── results.json
```

## Architecture

TestForge uses a deterministic CrewAI Flow with 7 specialized agents:

- **Repo Reader** — scans codebase structure and creates a context document
- **Scraper** — discovers API specs via MCP or OpenAPI endpoints
- **QA Analyst** — plans test strategy with prioritized test cases
- **BE Test Writer** — generates API-layer tests
- **FE Test Writer** — generates UI-layer tests with Page Object Models
- **E2E Test Writer** — generates cross-page user journey tests
- **Reviewer** — runs tests, categorizes failures, provides fix instructions

## Development

```bash
# Install in development mode
pip install -e .

# Run from source
py -m testforge --repo ./target --url https://app.example.com --creds creds.json
```

## License

MIT
