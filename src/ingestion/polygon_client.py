import json
import time
import logging
import asyncio
from web3 import AsyncWeb3, WebsocketProvider
from src.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PolymarketClient:
    def __init__(self, queue: asyncio.Queue):
        # We use AsyncWeb3 with WebSockets for true real-time, low-latency ingestion
        self.w3 = AsyncWeb3(WebsocketProvider(settings.POLYGON_WSS_URL))
        self.ctf_address = settings.POLYMARKET_CTF_ADDRESS
        self.queue = queue
        
        self.mock_abi = json.loads('''[
            {
                "anonymous": false,
                "inputs": [
                    {"indexed": true, "name": "maker", "type": "address"},
                    {"indexed": true, "name": "marketId", "type": "bytes32"},
                    {"indexed": false, "name": "outcome", "type": "uint256"},
                    {"indexed": false, "name": "size", "type": "uint256"},
                    {"indexed": false, "name": "price", "type": "uint256"}
                ],
                "name": "TradeExecuted",
                "type": "event"
            }
        ]''')
        
        self.contract = self.w3.eth.contract(address=self.w3.to_checksum_address(self.ctf_address), abi=self.mock_abi)

    async def listen_for_trades(self):
        """Polls for new block events via async websockets."""
        if not await self.w3.is_connected():
            logger.error("Failed to connect to Polygon WSS")
            return

        logger.info(f"Listening for trades on {self.ctf_address} via WSS...")
        
        event_filter = await self.contract.events.TradeExecuted.create_filter(fromBlock='latest')
        
        while True:
            try:
                new_entries = await event_filter.get_new_entries()
                for event in new_entries:
                    parsed_trade = self._parse_event(event)
                    # Push raw trade directly to async queue and return instantly
                    await self.queue.put(parsed_trade)
                await asyncio.sleep(1.0)
            except Exception as e:
                logger.error(f"Error polling wss events: {e}")
                await asyncio.sleep(5.0)

    def _parse_event(self, event):
        """Parse raw blockchain event into our internal Trade structure"""
        args = event['args']
        return {
            "transaction_hash": event['transactionHash'].hex(),
            "wallet_address": args['maker'],
            "market_id": args['marketId'].hex(),
            "outcome": "YES" if args['outcome'] == 1 else "NO",
            "size_usd": args['size'] / 1e6, # USDC 6 decimals
            "price": args['price'] / 1e6,
            "timestamp": int(time.time())
        }