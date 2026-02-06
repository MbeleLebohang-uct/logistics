# Order status updates middleware


sequenceDiagram
    autonumber
    participant Scheduler as Cloud Scheduler
    participant Producer as Producer Function
    participant Auth as Auth Middleware
    participant AuthDB as Firestore (Auth Tokens)
    participant StateDB as Firestore (System State)
    participant ShipAPI as Shipment API
    participant PubSub as Pub/Sub Topic<br/>(erp-order-status-update-queue)
    participant Consumer as Consumer Function
    participant ERP as Internal ERP

    note over Scheduler, Producer: Producer Flow
    Scheduler->>Producer: Trigger (every 3 min)
    
    %% Authentication Flow - Transparent gray background
    rect rgba(0, 0, 0, 0.5)
        note right of Producer: Authentication Flow
        Producer->>Auth: Request Auth Token
        Auth->>AuthDB: Get Encrypted Token (using REALM_ID)
        AuthDB-->>Auth: Return Encrypted Token
        Auth->>Auth: Decrypt Token (using SECRET_KEY)
        
        alt Token Expired?
            Auth->>Auth: Check Expiration
            opt Is Expired
                Auth->>Auth: Check Refresh Token Validity (100 days)
                alt Refresh Token Valid
                    Auth->>Auth: Refresh Token & Re-encrypt
                    Auth->>AuthDB: Save New Encrypted Token
                    Auth-->>Producer: Return Refreshed Token (200 OK)
                else Refresh Token Expired
                    Auth-->>Producer: Return Unauthorized (401)
                    Note right of Producer: Process Stops
                end
            end
        else Token Valid
            Auth-->>Producer: Return Token (200 OK)
        end
    end

    Producer->>StateDB: Get last_updated checkpoint
    StateDB-->>Producer: Return timestamp
    Producer->>ShipAPI: Poll for updates (using Token)
    ShipAPI-->>Producer: Return list of shipments
    
    loop For each shipment
        Producer->>PubSub: Publish Message
    end
    
    Producer->>StateDB: Update last_updated checkpoint

    note over PubSub, ERP: Consumer Flow
    PubSub->>Consumer: Push Message
    Consumer->>StateDB: Acquire Lock (Idempotency Check)
    
    alt Lock Acquired
        Consumer->>ERP: POST Update
        ERP-->>Consumer: 200 OK
        Consumer->>StateDB: Mark status as COMPLETED
    else Lock Failed / Already Processed
        Consumer-->>PubSub: Acknowledge (Skip)
    end
