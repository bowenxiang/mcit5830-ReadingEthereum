import random
import json
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from web3.providers.rpc import HTTPProvider

# BSC Testnet RPC URL provided in the assignment instructions
BSC_TESTNET_URL = "https://data-seed-prebsc-1-s1.binance.org:8545/"

# If you use one of the suggested infrastructure providers, the url will be of the form
# now_url  = f"https://eth.nownodes.io/{now_token}"
# alchemy_url = f"https://eth-mainnet.alchemyapi.io/v2/{alchemy_token}"
# infura_url = f"https://mainnet.infura.io/v3/{infura_token}"

# BSC Testnet RPC URL provided in the assignment instructions
BSC_TESTNET_URL = "https://data-seed-prebsc-1-s1.binance.org:8545/"

def connect_to_eth():
	"""
	Connects to the BSC Testnet.
	"""
	w3 = Web3(HTTPProvider(BSC_TESTNET_URL))
	if not w3.is_connected():
		raise ConnectionError("Failed to connect to the BSC Testnet RPC.")
	return w3


def connect_with_middleware(contract_json):
	"""
	Connects to BSC Testnet, loads the contract, and applies POA middleware.
	"""
	# TODO insert your code for this method from last week's assignment
	"""
	Connects to BSC Testnet, loads the contract, and applies POA middleware.
	"""
	# Connect to the BSC Testnet
	w3 = Web3(HTTPProvider(BSC_TESTNET_URL))
	if not w3.is_connected():
		raise ConnectionError("Failed to connect to the BSC Testnet RPC.")

	# Inject PoA middleware (required for BSC)
	w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

	# Load contract info from the provided JSON file
	with open(contract_json, 'r') as f:
		info = json.load(f)
	
	# Extract address and ABI for the 'bsc' network
	bsc_info = info.get('bsc', {})
	contract_address = bsc_info.get('address')
	contract_abi = bsc_info.get('abi')

	if not contract_address or not contract_abi:
		raise ValueError("Could not find 'bsc' address or abi in contract_info.json")

	# Instantiate the contract
	contract = w3.eth.contract(address=contract_address, abi=contract_abi)
	
	return w3, contract


def is_ordered_block(w3, block_num):
	"""
	Takes a block number
	Returns a boolean that tells whether all the transactions in the block are ordered by priority fee

	Before EIP-1559, a block is ordered if and only if all transactions are sorted in decreasing order of the gasPrice field

	After EIP-1559, there are two types of transactions
		*Type 0* The priority fee is tx.gasPrice - block.baseFeePerGas
		*Type 2* The priority fee is min( tx.maxPriorityFeePerGas, tx.maxFeePerGas - block.baseFeePerGas )

	Conveniently, most type 2 transactions set the gasPrice field to be min( tx.maxPriorityFeePerGas + block.baseFeePerGas, tx.maxFeePerGas )
	"""
	
	try:
		# Fetch the block with transaction hashes
		block = w3.eth.get_block(block_num, full_transactions=False)
	except Exception as e:
		print(f"Error fetching block {block_num}: {e}")
		return False # Or raise exception

	# Get baseFeePerGas, default to 0 if not present (pre-EIP-1559)
	base_fee_per_gas = block.get('baseFeePerGas', 0)
	
	transactions = block.get('transactions', [])
	if not transactions:
		return True  # An empty block is considered ordered

	priority_fees = []

	for tx_hash in transactions:
		try:
			# Get the full transaction object
			tx = w3.eth.get_transaction(tx_hash)
			
			tx_type = tx.get('type', 0) # Default to legacy type 0

			# Calculate priority fee based on transaction type
			if tx_type == 2:
				# Type 2 (EIP-1559)
				max_priority_fee = tx.get('maxPriorityFeePerGas', 0) or 0
				max_fee = tx.get('maxFeePerGas', 0) or 0
				
				priority_fee = min(max_priority_fee, max_fee - base_fee_per_gas)
			
			else:
				# Type 0 (Legacy) or EIP-2930 (Type 1)
				gas_price = tx.get('gasPrice', 0) or 0
				priority_fee = gas_price - base_fee_per_gas

			priority_fees.append(priority_fee)

		except Exception as e:
			print(f"Error processing transaction {tx_hash.hex()}: {e}")
			# Skip this transaction
			continue

	# Check if the list of priority fees is sorted in descending order
	for i in range(len(priority_fees) - 1):
		if priority_fees[i] < priority_fees[i+1]:
			return False
			
	return True


def get_contract_values():
	"""
	Connects to the contract and retrieves three values:
	1. The merkleRoot
	2. Whether admin_address has the DEFAULT_ADMIN_ROLE
	3. The prime associated with owner_address
	
	These values are retrieved from the contract at: 0xaA7CAaDA823300D18D3c43f65569a47e78220073
	"""
	
	# Connect to the chain and contract
	try:
		w3, contract = connect_with_middleware('contract_info.json')
	except Exception as e:
		print(f"Error connecting to contract: {e}")
		return None, None, None

	# Addresses and roles needed for the calls
	admin_address = "0xAC55e7d73A792fE1A9e051BDF4A010c33962809A"
	owner_address = "0x793A37a85964D96ACD6368777c7C7050F05b11dE"
	default_admin_role = int.to_bytes(0, 32, byteorder="big")

	try:
		# TODO complete the following lines by performing contract calls
		# Get and return the merkleRoot from the provided contract
		onchain_root = contract.functions.merkleRoot().call()
		
		# Check the contract to see if the address "admin_address" has the role "default_admin_role"
		has_role = contract.functions.hasRole(default_admin_role, admin_address).call()
		
		# Call the contract to get the prime owned by "owner_address"
		prime = contract.functions.getPrimeByOwner(owner_address).call()

	except Exception as e:
		print(f"Error during contract call: {e}")
		return None, None, None

	return onchain_root, has_role, prime


"""
This might be useful for testing (main is not run by the grader feel free to change 
this code anyway that is helpful)
"""
if __name__ == "__main__":
	# These are addresses associated with the Merkle contract (check on contract
	# functions and transactions on the block explorer at
	# https://testnet.bscscan.com/address/0xaA7CAaDA823300D18D3c43f65569a47e78220073
	
	# Test connection
	print("Testing connections...")
	try:
		w3_eth = connect_to_eth()
		print(f"connect_to_eth() successful. Connected: {w3_eth.is_connected()}")
		
		w3, contract = connect_with_middleware('contract_info.json')
		print(f"connect_with_middleware() successful. Contract address: {contract.address}")
	except Exception as e:
		print(f"Connection tests failed: {e}")

	# Test block ordering (Example block numbers from BSC testnet)
	# You can find recent blocks on https://testnet.bscscan.com/
	print("\nTesting block ordering...")
	# Note: You should test with actual recent blocks
	
	try:
		if 'w3' in locals() and w3.is_connected():
			latest_block_num = w3.eth.block_number
			print(f"Checking block {latest_block_num} for ordering...")
			ordered = is_ordered_block(w3, latest_block_num)
			print(f"Block {latest_block_num} is ordered: {ordered}")
			
			# Checking an older block that might have txs
			block_to_check = latest_block_num - 100 
			print(f"Checking block {block_to_check} for ordering...")
			ordered_check = is_ordered_block(w3, block_to_check)
			print(f"Block {block_to_check} is ordered: {ordered_check}")
		else:
			print("Skipping block ordering test, connection not established.")

	except Exception as e:
		print(f"Error checking block ordering: {e}")


	# Test contract values
	print("\nTesting contract values...")
	try:
		root, role, prime_val = get_contract_values()
		print(f"Merkle Root: {root}")
		print(f"Admin Has Role: {role}")
		print(f"Owner's Prime: {prime_val}")
	except Exception as e:
		print(f"Error getting contract values: {e}")