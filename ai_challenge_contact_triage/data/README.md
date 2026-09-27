# Data — incoming customer messages

`messages.jsonl` — one JSON object per line:

```json
{"id": "MSG-001", "channel": "chat | email | whatsapp", "received_at": "<ISO timestamp>", "from": "<sender>", "text": "<customer message, Spanish>"}
```

**This sample is synthetic and only a few hundred messages.** In production this is a
**high-volume** stream — on the order of **~10,000 messages per day**. The sample is just enough
to build and demonstrate your solution; design with the real volume in mind.

The messages are messy on purpose: mixed channels, informal Colombian Spanish, typos, some
multi-intent, some out of scope, and some pure noise.
