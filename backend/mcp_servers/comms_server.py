from fastmcp import FastMCP

mcp = FastMCP("comms_mcp")

@mcp.tool()
def send_notification(channel: str, message: str) -> dict:
    """Send alerts or messages to Slack/Teams channels"""
    return {"channel": channel, "message": message, "status": "sent"}

if __name__ == "__main__":
    mcp.run(transport="stdio")