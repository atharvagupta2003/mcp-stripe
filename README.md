# MCP Stripe Server
[![smithery badge](https://smithery.ai/badge/@atharvagupta2003/mcp-stripe)](https://smithery.ai/server/@atharvagupta2003/mcp-stripe)

A Model Context Protocol (MCP) server implementation that integrates with Stripe for handling payments, customers, and refunds. This server provides a structured API to manage financial transactions securely.

## Requirements
- Python 3.8+
- MCP SDK 0.1.0+
- Stripe Python SDK
- dotenv

## Components

### Resources
The server provides audit logging of all Stripe operations:

- Stores audit logs of customer, payment, and refund operations
- Supports structured logging for better traceability
- Uses MCP resource endpoints to retrieve audit data

### Tools
The server implements Stripe API operations, including:

#### Customer Management
- **customer_create**: Create a new customer
- **customer_retrieve**: Retrieve a customer's details
- **customer_update**: Update customer information

#### Payment Operations
- **payment_intent_create**: Create a payment intent for processing payments
- **charge_list**: List recent charges

#### Refund Operations
- **refund_create**: Create a refund for a charge

## Features
- **Secure Payments**: Integrates with Stripe for robust payment handling
- **Audit Logging**: Keeps track of all Stripe transactions
- **Error Handling**: Comprehensive error handling with clear messages
- **MCP Integration**: Supports MCP-compatible tools and resource listing

## Installation

### Installing via Smithery

To install Stripe Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@atharvagupta2003/mcp-stripe):

```bash
npx -y @smithery/cli install @atharvagupta2003/mcp-stripe --client claude
```

### Install dependencies
```sh
python -m venv venv
source venv/bin/activate  # On macOS/Linux
venv\Scripts\activate    # On Windows
pip install -e .
```

### Configuration
Set up the environment variables in a `.env` file:
```sh
STRIPE_API_KEY=your_stripe_secret_key
```

#### Claude Desktop

Add the server configuration to your Claude Desktop config:

Windows: C:\Users\<username>\AppData\Roaming\Claude\claude_desktop_config.json

MacOS: ~/Library/Application Support/Claude/claude_desktop_config.json

```
{
  "mcpServers": {
    "stripe": {
      "command": "uv",
      "args": [
        "--directory",
        "/ABSOLUTE/PATH/TO/PARENT/FOLDER/src",
        "run",
        "server.py"
      ]
    }
  }
}
```

## Usage

### Start the server
```sh
uv run src/server.py
```


### Example MCP Commands

#### Create a customer
```json
{
    "tool": "customer_create",
    "arguments": {
        "email": "customer@example.com",
        "name": "John Doe"
    }
}
```

#### Retrieve a customer
```json
{
    "tool": "customer_retrieve",
    "arguments": {
        "customer_id": "cus_123456"
    }
}
```

#### Create a payment intent
```json
{
    "tool": "payment_intent_create",
    "arguments": {
        "amount": 5000,
        "currency": "usd",
        "customer": "cus_123456"
    }
}
```

#### Create a refund
```json
{
    "tool": "refund_create",
    "arguments": {
        "charge_id": "ch_abc123"
    }
}
```

## Error Handling
The server provides clear error messages for common scenarios:
- **Missing API Key**: STRIPE_API_KEY required
- **Invalid API Key**: Authentication error
- **Customer not found**: Invalid customer ID
- **Invalid input**: Missing or incorrect parameters

## Development
### Testing
Run the MCP Inspector for interactive testing:
```sh
npx @modelcontextprotocol/inspector uv --directory /ABSOLUTE/PATH/TO/PARENT/FOLDER/src run server.py
```

### Building
1. Update dependencies:
```
uv compile pyproject.toml
```
2. Build package:
```
uv build
```

### Contributing
We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
