# type-a-cmp-mcp

A FastMCP server that wraps a REST API as MCP tools.

## Overview

This is a [FastMCP](https://github.com/jlowin/fastmcp) server that exposes a
REST API as a set of MCP (Model Context Protocol) tools. AI agents and LLMs can
invoke these tools to interact with the upstream API.

## Local Development

### Prerequisites

- Python 3.11+
- The upstream API running at `http://localhost:8080`

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run

```bash
python3 mcp_server.py
```

The server starts on `http://0.0.0.0:8000/mcp` using the
streamable HTTP transport.

## Container Build

```bash
docker build -t type-a-cmp-mcp .
docker run -p 8000:8000 type-a-cmp-mcp
```

## CI/CD (Tekton)

Every push to `main` automatically builds the container image and deploys to
OpenShift. No pipeline files are stored in this repo -- CI/CD is handled by a
shared Tekton Pipeline pre-provisioned on the cluster.

The shared pipeline (`fastmcp-ci-cd`) performs:

1. **Clone** -- fetches the repository source
2. **Build** -- builds the container image with buildah and pushes to the
   OpenShift internal registry
3. **Deploy** -- applies the deployment manifests and rolls out the new version

### How It Works

A GitHub webhook (created automatically by the RHDH template) sends push events
to a shared Tekton EventListener on OpenShift. The EventListener extracts the
repo URL, revision, and name from the webhook payload and creates a PipelineRun
against the shared `fastmcp-ci-cd` Pipeline.

### Manual Deployment (without pipeline)

Apply the included manifests directly:

```bash
oc apply -f deploy/deployment.yaml
```

This creates a Deployment, Service, and Route in the `mcp-servers`
namespace. The Route provides a TLS-terminated public endpoint.

## Customization

Edit `mcp_server.py` to replace the placeholder tools (`list_items`,
`get_item`, `create_item`) with tools that match your actual API endpoints.
Each `@mcp.tool` function maps to one REST endpoint:

| HTTP Method | MCP Tool Pattern |
|-------------|-----------------|
| GET (list)  | Tool that returns a list of resources |
| GET (by id) | Tool that returns a single resource |
| POST        | Tool that creates a resource |
| PATCH / PUT | Tool that updates a resource |
| DELETE      | Tool that removes a resource |
