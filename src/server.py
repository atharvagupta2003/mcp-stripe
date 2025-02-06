# stripe_server/server.py (updated with logging)
import os
import json
import logging
from datetime import datetime
from typing import Any, Sequence
from functools import lru_cache
import stripe
from dotenv import load_dotenv
import mcp.server.stdio
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Resource, Tool, TextContent
from pydantic import AnyUrl
from tools import get_stripe_tools

load_dotenv()
logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG") else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("stripe-mcp-server")

def custom_json_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, stripe.StripeObject):
        return json.loads(str(obj))
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

# In server.py - Revised StripeManager class
class StripeManager:
    def __init__(self):
        logger.info("🔄 Initializing StripeManager")
        self.audit_entries = []  # MUST be first line in __init__
        stripe.api_key = os.getenv("STRIPE_API_KEY")
        
        if not stripe.api_key:
            logger.critical("❌ STRIPE_API_KEY missing")
            raise ValueError("STRIPE_API_KEY required")
        
        logger.info("✅ Stripe configured")
        logger.debug("Test connection...")
        try:  # Verify API key works
            stripe.Customer.list(limit=1)
        except stripe.error.AuthenticationError as e:
            logger.critical("🔴 Invalid API key: %s", e)
            raise

    def log_operation(self, operation: str, parameters: dict) -> None:
        logger.debug("📝 Logging operation: %s with params: %s", operation, parameters)
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "parameters": parameters
        }
        self.audit_entries.append(audit_entry)

    def _synthesize_audit_log(self) -> str:
        logger.debug("Generating audit log with %d entries", len(self.audit_entries))
        if not self.audit_entries:
            return "No Stripe operations performed yet."
        
        report = "📋 Stripe Operations Audit Log 📋\n\n"
        for entry in self.audit_entries:
            report += f"[{entry['timestamp']}]\n"
            report += f"Operation: {entry['operation']}\n"
            report += f"Parameters: {json.dumps(entry['parameters'], indent=2)}\n"
            report += "-" * 50 + "\n"
        return report


async def main():
    logger.info("Starting Stripe MCP Server")
    manager = StripeManager()
    server = Server("stripe-mcp-server")

    @server.list_resources()
    async def handle_list_resources() -> list[Resource]:
        return [
            Resource(
                uri=AnyUrl("audit://stripe-operations"),
                name="Stripe Operations Audit Log",
                description="Log of all Stripe operations performed",
                mimeType="text/plain",
            )
        ]

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> str:
        if uri.scheme != "audit":
            raise ValueError("Unsupported URI scheme")
        return manager._synthesize_audit_log()

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return get_stripe_tools()

    @server.call_tool()
    async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
        try:
            if name.startswith("customer_"):
                return await handle_customer_operations(manager, name, arguments)
            elif name.startswith("payment_"):
                return await handle_payment_operations(manager, name, arguments)
            elif name.startswith("refund_"):
                return await handle_refund_operations(manager, name, arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error: {str(e)}")
            raise RuntimeError(f"Payment processing failed: {str(e)}")

    async def handle_customer_operations(manager, name: str, args: dict):
        if name == "customer_create":
            customer = stripe.Customer.create(
                email=args["email"],
                name=args.get("name"),
                metadata=args.get("metadata", {})
            )
            manager.log_operation("customer_create", args)
            return [TextContent(text=json.dumps(customer, default=custom_json_serializer))]
        
        elif name == "customer_retrieve":
            customer = stripe.Customer.retrieve(args["customer_id"])
            return [TextContent(text=json.dumps(customer, default=custom_json_serializer))]
        
        elif name == "customer_update":
            customer = stripe.Customer.modify(
                args["customer_id"],
                **args["update_fields"]
            )
            manager.log_operation("customer_update", args)
            return [TextContent(text=json.dumps(customer, default=custom_json_serializer))]
        
        raise ValueError(f"Unknown customer operation: {name}")

    async def handle_payment_operations(manager, name: str, args: dict):
        if name == "payment_intent_create":
            intent = stripe.PaymentIntent.create(
                amount=args["amount"],
                currency=args["currency"],
                payment_method_types=args.get("payment_method_types", ["card"]),
                customer=args.get("customer"),
                metadata=args.get("metadata", {})
            )
            manager.log_operation("payment_intent_create", args)
            return [TextContent(text=json.dumps(intent, default=custom_json_serializer))]
        
        elif name == "charge_list":
            charges = stripe.Charge.list(
                limit=args.get("limit", 10),
                customer=args.get("customer_id")
            )
            return [TextContent(text=json.dumps(charges, default=custom_json_serializer))]
        
        raise ValueError(f"Unknown payment operation: {name}")

    async def handle_refund_operations(manager, name: str, args: dict):
        if name == "refund_create":
            refund = stripe.Refund.create(
                charge=args["charge_id"],
                amount=args.get("amount"),
                reason=args.get("reason", "requested_by_customer")
            )
            manager.log_operation("refund_create", args)
            return [TextContent(text=json.dumps(refund, default=custom_json_serializer))]
        
        raise ValueError(f"Unknown refund operation: {name}")

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-server-stripe",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

