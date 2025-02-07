# main.py
import os
import json
import logging
from datetime import datetime
from typing import Any, List, Sequence
import asyncio

import stripe
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from urllib.parse import urlparse

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG") else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("stripe-fastapi-server")

# -------------------------------------------------------------------
# Pydantic Models
# -------------------------------------------------------------------

class Resource(BaseModel):
    uri: str
    name: str
    description: str
    mimeType: str

class Tool(BaseModel):
    name: str
    description: str

class TextContent(BaseModel):
    text: str

class CallToolRequest(BaseModel):
    name: str
    arguments: dict

# -------------------------------------------------------------------
# Utility Functions
# -------------------------------------------------------------------

def custom_json_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, stripe.StripeObject):
        return json.loads(str(obj))
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

# A stub for get_stripe_tools.
# (In your actual code, this may load more dynamic or detailed tool info.)
def get_stripe_tools() -> List[Tool]:
    return [
        Tool(
            name="customer_create",
            description="Create a new Stripe customer."
        ),
        Tool(
            name="payment_intent_create",
            description="Create a new Payment Intent."
        ),
        Tool(
            name="refund_create",
            description="Create a refund for a charge."
        )
    ]

# -------------------------------------------------------------------
# StripeManager Class
# -------------------------------------------------------------------

class StripeManager:
    def __init__(self):
        logger.info("🔄 Initializing StripeManager")
        self.audit_entries = []  # MUST be first line in __init__
        stripe.api_key = os.getenv("STRIPE_API_KEY")
        
        if not stripe.api_key:
            logger.critical("❌ STRIPE_API_KEY missing")
            raise ValueError("STRIPE_API_KEY required")
        
        logger.info("✅ Stripe configured")
        # Removed the call to asyncio.run() from here.

    async def _test_stripe_connection(self):
        # This method remains async and will be awaited in the startup event.
        return await asyncio.to_thread(stripe.Customer.list, limit=1)

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

# -------------------------------------------------------------------
# FastAPI App Initialization
# -------------------------------------------------------------------


app = FastAPI(title="Stripe FastAPI Server")
manager: StripeManager = None  # Will be set on startup

@app.on_event("startup")
async def startup_event():
    global manager
    try:
        manager = StripeManager()
        # Now await the async connection test:
        customers = await manager._test_stripe_connection()
        logger.debug("Stripe connection test returned: %s", customers)
    except Exception as e:
        logger.error("Error during startup: %s", e)
        raise

# -------------------------------------------------------------------
# Endpoint Definitions
# -------------------------------------------------------------------

@app.get("/resources", response_model=List[Resource])
async def list_resources():
    """
    Returns a list of resources. In this example, we only expose the audit log.
    """
    return [
        Resource(
            uri="audit://stripe-operations",
            name="Stripe Operations Audit Log",
            description="Log of all Stripe operations performed",
            mimeType="text/plain",
        )
    ]

@app.get("/resource")
async def read_resource(uri: str = Query(..., description="The URI of the resource")):
    """
    Reads a resource. For our case, if the scheme is 'audit', returns the audit log.
    """
    parsed = urlparse(uri)
    if parsed.scheme != "audit":
        raise HTTPException(status_code=400, detail="Unsupported URI scheme")
    return {"audit_log": manager._synthesize_audit_log()}

@app.get("/tools", response_model=List[Tool])
async def list_tools():
    """
    Returns the list of available Stripe tools.
    """
    return get_stripe_tools()

# -------------------------------------------------------------------
# Tool Call Handlers (wrapped as async functions)
# -------------------------------------------------------------------

async def handle_customer_operations(manager: StripeManager, name: str, args: dict) -> List[TextContent]:
    if name == "customer_create":
        customer = await asyncio.to_thread(
            stripe.Customer.create,
            email=args["email"],
            name=args.get("name"),
            metadata=args.get("metadata", {})
        )
        manager.log_operation("customer_create", args)
        return [TextContent(text=json.dumps(customer, default=custom_json_serializer))]
    
    elif name == "customer_retrieve":
        customer = await asyncio.to_thread(stripe.Customer.retrieve, args["customer_id"])
        return [TextContent(text=json.dumps(customer, default=custom_json_serializer))]
    
    elif name == "customer_update":
        customer = await asyncio.to_thread(
            stripe.Customer.modify,
            args["customer_id"],
            **args["update_fields"]
        )
        manager.log_operation("customer_update", args)
        return [TextContent(text=json.dumps(customer, default=custom_json_serializer))]
    
    raise HTTPException(status_code=400, detail=f"Unknown customer operation: {name}")

async def handle_payment_operations(manager: StripeManager, name: str, args: dict) -> List[TextContent]:
    if name == "payment_intent_create":
        intent = await asyncio.to_thread(
            stripe.PaymentIntent.create,
            amount=args["amount"],
            currency=args["currency"],
            payment_method_types=args.get("payment_method_types", ["card"]),
            customer=args.get("customer"),
            metadata=args.get("metadata", {})
        )
        manager.log_operation("payment_intent_create", args)
        return [TextContent(text=json.dumps(intent, default=custom_json_serializer))]
    
    elif name == "charge_list":
        charges = await asyncio.to_thread(
            stripe.Charge.list,
            limit=args.get("limit", 10),
            customer=args.get("customer_id")
        )
        return [TextContent(text=json.dumps(charges, default=custom_json_serializer))]
    
    raise HTTPException(status_code=400, detail=f"Unknown payment operation: {name}")

async def handle_refund_operations(manager: StripeManager, name: str, args: dict) -> List[TextContent]:
    if name == "refund_create":
        refund = await asyncio.to_thread(
            stripe.Refund.create,
            charge=args["charge_id"],
            amount=args.get("amount"),
            reason=args.get("reason", "requested_by_customer")
        )
        manager.log_operation("refund_create", args)
        return [TextContent(text=json.dumps(refund, default=custom_json_serializer))]
    
    raise HTTPException(status_code=400, detail=f"Unknown refund operation: {name}")

@app.post("/tools/call", response_model=List[TextContent])
async def call_tool(request: CallToolRequest):
    """
    Calls a specific Stripe tool based on the provided name and arguments.
    """
    logger.debug("=== RECEIVED call_tool request ===")
    name = request.name
    arguments = request.arguments
    try:
        if name.startswith("customer_"):
            return await handle_customer_operations(manager, name, arguments)
        elif name.startswith("payment_"):
            return await handle_payment_operations(manager, name, arguments)
        elif name.startswith("refund_"):
            return await handle_refund_operations(manager, name, arguments)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {name}")
    except stripe.error.StripeError as e:
        logger.error(f"Stripe API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Payment processing failed: {str(e)}")
