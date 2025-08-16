-----

## 🚀 Feature Update (Day 15): Real-time WebSocket Endpoint

As part of the \#30DaysofVoiceAgents challenge, this update establishes the foundational real-time communication layer for **Dhwani Bot**. A WebSocket endpoint has been created to enable persistent, two-way interaction between the client and the server.

The immediate goal of this feature is to create a proof-of-concept for real-time communication. This "echo server" is the first step toward implementing advanced features like streaming audio for transcription and receiving AI responses chunk-by-chunk.

-----

### 🔧 Implementation Details

The new functionality is implemented within `main.py` using FastAPI's native `WebSocket` support.

  * An endpoint is created at the path `/ws`.
  * When a client connects, the server accepts the connection.
  * The server then enters a loop, listening for incoming text messages.
  * Upon receiving a message, it sends the same message back to the client, prefixed with ` Echo:  `.
<img width="1365" height="767" alt="image" src="https://github.com/user-attachments/assets/8f2ebccc-e12f-4866-ad2b-2d457b463d15" />

