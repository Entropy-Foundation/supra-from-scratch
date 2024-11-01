from typing import Any, Optional

from aptos_sdk.account_address import AccountAddress
from aptos_sdk.bcs import Deserializer, Serializer
from aptos_sdk.transactions import Script, EntryFunction


class TransactionPayload:
    SCRIPT: int = 0
    SCRIPT_FUNCTION: int = 2
    MULTISIG: int = 3

    variant: int
    value: Any

    def __init__(self, payload: Any):
        if isinstance(payload, Script):
            self.variant = TransactionPayload.SCRIPT
        elif isinstance(payload, EntryFunction):
            self.variant = TransactionPayload.SCRIPT_FUNCTION
        elif isinstance(payload, Multisig):
            self.variant = TransactionPayload.MULTISIG
        else:
            raise Exception("Invalid type")
        self.value = payload

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TransactionPayload):
            return NotImplemented
        return self.variant == other.variant and self.value == other.value

    def __str__(self) -> str:
        return self.value.__str__()

    @staticmethod
    def deserialize(deserializer: Deserializer) -> "TransactionPayload":
        variant = deserializer.uleb128()

        if variant == TransactionPayload.SCRIPT:
            payload: Any = Script.deserialize(deserializer)
        elif variant == TransactionPayload.SCRIPT_FUNCTION:
            payload = EntryFunction.deserialize(deserializer)
        elif variant == TransactionPayload.MULTISIG:
            payload = Multisig.deserialize(deserializer)
        else:
            raise Exception("Invalid type")

        return TransactionPayload(payload)

    def serialize(self, serializer: Serializer) -> None:
        serializer.uleb128(self.variant)
        self.value.serialize(serializer)


class MultiSigTransactionPayload:
    transaction_payload: EntryFunction

    def __init__(self, transaction_payload: EntryFunction):
        self.transaction_payload = transaction_payload

    def serialize(self, serializer: Serializer):
        # For now, we only support EntryFunction payloads
        serializer.uleb128(0)
        self.transaction_payload.serialize(serializer)

    @classmethod
    def deserialize(cls, deserializer: Deserializer):
        deserializer.uleb128()  # For now, this is always 0
        transaction_payload = EntryFunction.deserialize(deserializer)
        return cls(transaction_payload)


class Multisig:
    multisig_address: AccountAddress
    transaction_payload: MultiSigTransactionPayload

    def __init__(self, multisig_address: AccountAddress,
                 transaction_payload: Optional[MultiSigTransactionPayload] = None):
        self.multisig_address = multisig_address
        self.transaction_payload = transaction_payload

    def serialize(self, serializer: Serializer):
        self.multisig_address.serialize(serializer)
        serializer.bool(self.transaction_payload is not None)
        if self.transaction_payload is not None:
            self.transaction_payload.serialize(serializer)

    @classmethod
    def deserialize(cls, deserializer: Deserializer):
        multisig_address = AccountAddress.deserialize(deserializer)
        payload_present = deserializer.bool()
        transaction_payload = None
        if payload_present:
            transaction_payload = MultiSigTransactionPayload.deserialize(deserializer)
        return cls(multisig_address, transaction_payload)


def payload_to_dict(obj: Any) -> dict[str, Any]:
    result = {}
    for k, v in obj.__dict__.items():
        if k.startswith("_") or k == "prehash":
            pass
        elif isinstance(v, TransactionPayload):
            if isinstance(v.value, EntryFunction):
                result[k] = {"EntryFunction": payload_to_dict(v.value)}
            elif isinstance(v.value, Multisig):
                result[k] = {"Multisig": payload_to_dict(v.value)}
            elif isinstance(v.value, Script):
                result[k] = {"Script": payload_to_dict(v.value)}
            else:
                raise Exception("Unknown payload type")
        elif isinstance(v, MultiSigTransactionPayload):
            result[k] = {"EntryFunction": payload_to_dict(v.transaction_payload)}
        elif isinstance(v, AccountAddress):
            result[k] = str(v)
        elif k == "args":
            result[k] = [list(item) for item in v]
        elif k == "expiration_timestamps_secs":
            result["expiration_timestamp_secs"] = v
        elif hasattr(v, "__dict__"):
            result[k] = payload_to_dict(v)  # Recursively handle nested objects
        else:
            result[k] = v
    return result
