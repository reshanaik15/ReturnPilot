# Requirements Document

## Introduction

This document specifies the requirements for migrating the ReturnPilot frontend prototype into a production-ready full-stack application. The current implementation is a single-file React application with all logic in the frontend, including exposed API keys and no data persistence. The migration will separate concerns into a proper three-tier architecture: React frontend, FastAPI/Node.js backend with agent orchestration, and Supabase (PostgreSQL) database, following the hackathon playbook specifications.

## Glossary

- **Frontend**: The React-based user interface that customers interact with
- **Backend**: The FastAPI or Node.js API server that orchestrates agent logic and handles business operations
- **Database**: The Supabase PostgreSQL instance that persists all application data
- **Agent_Loop**: The backend orchestration loop that manages Claude API tool-use cycles
- **Customer**: An end-user who purchased items and may initiate returns
- **Business_User**: An internal operator viewing the operations dashboard
- **Return_Record**: A database entry representing a single return request with status and metadata
- **Tool**: A function exposed to Claude for performing specific actions (search_orders, check_policy, etc.)
- **Reasoning_Trace**: The sequence of tool calls and results showing agent decision-making
- **Photo_Evidence**: Customer-uploaded images stored in Supabase Storage for damage verification
- **Notification_System**: The external service (viaSocket/Twilio/SendGrid) for alerts
- **Session**: A customer's interaction period with the chat interface
- **State_Machine**: The progression of return status: initiated → shipped → refunded or declined

## Requirements

### Requirement 1: Secure API Key Management

**User Story:** As a security-conscious developer, I want all sensitive credentials stored server-side, so that API keys are never exposed to the browser.

#### Acceptance Criteria

1. THE Backend SHALL load the Claude API key from environment variables only
2. THE Frontend SHALL NOT contain any hardcoded API keys or sensitive credentials
3. WHEN the Frontend needs agent interaction, THE Frontend SHALL call Backend endpoints without exposing credentials
4. THE Backend SHALL validate all incoming requests before forwarding to Claude API
5. THE Backend SHALL return error responses when API keys are missing or invalid

### Requirement 2: Data Persistence Layer

**User Story:** As a customer, I want my return data to persist across sessions, so that I can return later and check status.

#### Acceptance Criteria

1. THE Database SHALL store customers, orders, return_policy, returns, return_evidence, and notifications_log tables
2. THE customers table SHALL include id, name, email, and contact fields
3. THE orders table SHALL include id, customer_id, item_name, category, price, purchase_date, and final_sale fields
4. THE return_policy table SHALL include category, window_days, exclusions, and notes fields
5. THE returns table SHALL include id, order_id, status, reason, agent_reasoning_log, created_at, and updated_at fields
6. THE return_evidence table SHALL include id, return_id, photo_url, claimed_issue, ai_verdict, confidence, ai_notes, and reviewed_by_human fields
7. THE notifications_log table SHALL include return_id, message, sent_at, and trigger_reason fields
8. WHEN a page refresh occurs, THE Frontend SHALL retrieve current state from the Backend
9. WHEN a server restart occurs, THE Backend SHALL read all state from the Database
10. THE Database SHALL enforce foreign key constraints between related tables

### Requirement 3: Backend Agent Orchestration Loop

**User Story:** As a developer, I want the agent logic to run server-side in a proper tool-use loop, so that complex multi-step reasoning works correctly.

#### Acceptance Criteria

1. THE Backend SHALL implement a complete Claude tool-use orchestration loop
2. WHEN a tool_use block is returned by Claude, THE Backend SHALL execute the tool locally and send the result back to Claude
3. THE Backend SHALL continue the loop until Claude returns a text response without tool_use blocks
4. THE Backend SHALL enforce a maximum iteration limit of 6 tool-use cycles per message
5. WHEN the iteration limit is exceeded, THE Backend SHALL return a graceful message and preserve conversation state
6. THE Backend SHALL append all tool calls and results to the reasoning trace for each message
7. THE Backend SHALL maintain conversation history in memory or database for session continuity

### Requirement 4: Multi-User Support

**User Story:** As a business operator, I want multiple customers to use the system simultaneously, so that the application scales properly.

#### Acceptance Criteria

1. THE Backend SHALL support concurrent requests from multiple customers without data leakage
2. WHEN a customer is authenticated, THE Backend SHALL filter all data queries by customer_id
3. THE Database SHALL isolate customer data through proper WHERE clauses in all queries
4. THE Backend SHALL return only returns, orders, and evidence belonging to the authenticated customer
5. THE Business_User dashboard SHALL display all returns across all customers without filtering

### Requirement 5: RESTful API Endpoints

**User Story:** As a frontend developer, I want well-defined API endpoints, so that I can integrate the UI cleanly with the backend.

#### Acceptance Criteria

1. THE Backend SHALL expose POST /api/agent/message accepting customer_id, message text, and optional image
2. THE Backend SHALL expose GET /api/orders/search accepting customer_id and query parameters
3. THE Backend SHALL expose GET /api/policy/check accepting order_id
4. THE Backend SHALL expose POST /api/returns/initiate accepting order_id and reason
5. THE Backend SHALL expose POST /api/returns/verify-photo accepting return_id, photo file, claimed_issue
6. THE Backend SHALL expose GET /api/returns/:id returning return status and metadata
7. THE Backend SHALL expose GET /api/dashboard/returns returning all return records for business view
8. WHEN any endpoint receives invalid parameters, THE Backend SHALL return a 400 status with error details
9. WHEN any endpoint encounters a server error, THE Backend SHALL return a 500 status with a safe error message

### Requirement 6: Photo Upload and Storage

**User Story:** As a customer claiming damage, I want to upload photos as evidence, so that my return can be verified visually.

#### Acceptance Criteria

1. THE Frontend SHALL allow customers to select and upload image files
2. THE Backend SHALL accept image uploads in JPEG, PNG, and WebP formats
3. THE Backend SHALL upload photos to Supabase Storage in a returns-evidence bucket
4. THE Backend SHALL store the public URL in the return_evidence table photo_url field
5. THE Backend SHALL pass the image to Claude as base64 for AI analysis
6. WHEN a photo upload fails, THE Backend SHALL return an error without creating evidence records
7. THE Database SHALL link photo evidence to returns via return_id foreign key

### Requirement 7: Notification Integration

**User Story:** As a customer, I want to receive notifications at key milestones, so that I know when my return is approved or refunded.

#### Acceptance Criteria

1. THE Backend SHALL integrate with viaSocket, Twilio, or SendGrid for notifications
2. WHEN a return status changes to "initiated", THE Backend SHALL send an approval notification
3. WHEN a return status changes to "refunded", THE Backend SHALL send a refund confirmation notification
4. WHEN a return is flagged for human review, THE Backend SHALL send an internal alert to business operators
5. THE Backend SHALL NOT send notifications for intermediate tool calls or minor state changes
6. THE Backend SHALL log all sent notifications to the notifications_log table
7. WHEN a notification fails to send, THE Backend SHALL log the error and continue processing

### Requirement 8: Alternative Offer Handling

**User Story:** As a customer with an ineligible return, I want to receive alternative offers, so that I have options instead of a flat rejection.

#### Acceptance Criteria

1. WHEN check_policy returns ineligible, THE Agent_Loop SHALL include an alternative offer in the response
2. THE Agent_Loop SHALL offer store credit as one alternative for ineligible returns
3. THE Agent_Loop SHALL offer exchange for a different size or color as another alternative
4. THE Agent_Loop SHALL explain the specific reason for ineligibility in plain language
5. THE Agent_Loop SHALL NOT proceed to initiate_return when an order is ineligible

### Requirement 9: Multi-Match Clarification

**User Story:** As a customer with multiple similar orders, I want the agent to ask clarifying questions, so that the correct order is selected.

#### Acceptance Criteria

1. WHEN search_orders returns multiple matches, THE Agent_Loop SHALL list all candidates with item name, price, and purchase date
2. THE Agent_Loop SHALL ask the customer to specify which order they mean
3. THE Agent_Loop SHALL NOT call initiate_return until the customer has clarified their selection
4. THE Agent_Loop SHALL wait for the customer's next message before proceeding
5. WHEN search_orders returns zero matches, THE Agent_Loop SHALL inform the customer and suggest rephrasing

### Requirement 10: Reasoning Trace Persistence

**User Story:** As a business analyst, I want to review the agent's reasoning for each return, so that I can audit decisions and improve the system.

#### Acceptance Criteria

1. THE Backend SHALL serialize the reasoning trace as JSON for each agent message
2. THE Backend SHALL store the reasoning trace in the returns table agent_reasoning_log field
3. THE Frontend SHALL retrieve and display the reasoning trace from the database
4. THE reasoning trace SHALL include tool names, inputs, and result summaries for each step
5. WHEN a return has multiple interactions, THE Backend SHALL append new reasoning steps to the existing log

### Requirement 11: Real-Time Dashboard Updates

**User Story:** As a business operator, I want the dashboard to reflect current state, so that I can monitor returns accurately.

#### Acceptance Criteria

1. THE Frontend dashboard SHALL fetch return data from GET /api/dashboard/returns
2. WHEN a return status changes, THE Backend SHALL update the returns table immediately
3. THE Frontend dashboard SHALL poll the endpoint every 5 seconds or use webhooks for updates
4. THE dashboard SHALL display return_id, customer name, item name, reason, status, and AI verdict
5. THE dashboard SHALL show a separate section for returns flagged for human review

### Requirement 12: Human Review Workflow

**User Story:** As a business operator, I want to approve or decline flagged returns, so that I can provide final judgment on unclear cases.

#### Acceptance Criteria

1. THE Backend SHALL expose POST /api/returns/:id/review accepting approve or decline action
2. WHEN a return is flagged for review, THE Backend SHALL set flagged_for_review to true
3. WHEN a Business_User approves a flagged return, THE Backend SHALL keep the current status and clear the flag
4. WHEN a Business_User declines a flagged return, THE Backend SHALL update status to "declined"
5. THE Backend SHALL record reviewed_by_human as true in the return_evidence table
6. THE Frontend dashboard SHALL display approve and decline buttons for flagged returns

### Requirement 13: State Machine Transitions

**User Story:** As a business operator, I want to advance return status through the workflow, so that returns progress toward completion.

#### Acceptance Criteria

1. THE Backend SHALL expose POST /api/returns/:id/advance for manual status progression
2. WHEN status is "initiated" and advance is called, THE Backend SHALL update status to "shipped"
3. WHEN status is "shipped" and advance is called, THE Backend SHALL update status to "refunded"
4. WHEN status is "refunded" or "declined", THE Backend SHALL reject advance requests
5. WHEN status changes to "refunded", THE Backend SHALL trigger a refund notification
6. THE Backend SHALL update the updated_at timestamp on every status change

### Requirement 14: UI Preservation

**User Story:** As a user familiar with the prototype, I want the UI to remain unchanged, so that the migration is seamless.

#### Acceptance Criteria

1. THE Frontend SHALL preserve the existing chat interface layout and styling
2. THE Frontend SHALL preserve the existing dashboard layout and table structure
3. THE Frontend SHALL preserve the reasoning trace panel appearance
4. THE Frontend SHALL preserve the photo upload button and image preview
5. THE Frontend SHALL replace direct Claude API calls with Backend endpoint calls
6. THE Frontend SHALL display identical status pills and icons for return states
7. THE Frontend SHALL maintain the same customer login screen

### Requirement 15: Deployment Readiness

**User Story:** As a DevOps engineer, I want the application to be deployable on modern hosting platforms, so that it can be launched in production.

#### Acceptance Criteria

1. THE Frontend SHALL be configured for deployment on Vercel
2. THE Backend SHALL be configured for deployment on Render or equivalent container platform
3. THE Database SHALL use Supabase managed PostgreSQL
4. THE Backend SHALL read database connection strings from environment variables
5. THE Backend SHALL include a health check endpoint at GET /api/health
6. THE Frontend SHALL use environment variables for Backend API base URL
7. THE project SHALL include separate package.json files for frontend and backend with proper dependencies

### Requirement 16: Error Handling and Resilience

**User Story:** As a customer, I want clear error messages when something fails, so that I understand what went wrong.

#### Acceptance Criteria

1. WHEN the Claude API returns an error, THE Backend SHALL return a user-friendly message to the Frontend
2. WHEN the Database connection fails, THE Backend SHALL return a 503 status with a retry suggestion
3. WHEN a tool execution fails, THE Backend SHALL log the error and return a partial response if possible
4. THE Frontend SHALL display error messages in the chat interface without breaking the UI
5. THE Frontend SHALL show a loading spinner during Backend requests
6. WHEN a network request times out, THE Frontend SHALL display a timeout message and allow retry

### Requirement 17: Migration Data Seeding

**User Story:** As a developer, I want to seed the database with demo data, so that the migrated application works immediately.

#### Acceptance Criteria

1. THE Backend SHALL include a database migration script that creates all required tables
2. THE Backend SHALL include a seed script that populates customers, orders, and return_policy tables
3. THE seed script SHALL insert the same 3 customers used in the prototype
4. THE seed script SHALL insert the same 24 orders used in the prototype
5. THE seed script SHALL insert return policy rules for all 6 categories
6. THE Backend SHALL run migrations automatically on first deployment or provide clear setup instructions
