# Implementation Plan: Backend Architecture Migration

## Overview

This implementation plan transforms the single-file React prototype (ReturnPilot.jsx) into a production-ready three-tier architecture with React frontend, FastAPI (Python) backend, and Supabase PostgreSQL database. The migration focuses on separating concerns, securing credentials, persisting data, and maintaining the existing UI experience while implementing server-side agent orchestration.

## Tasks

- [x] 1. Set up project structure and configuration
  - Create backend directory with FastAPI application structure
  - Create frontend directory for React application
  - Set up Python virtual environment and install dependencies (fastapi, uvicorn, sqlalchemy, psycopg2-binary, anthropic, httpx, pydantic, python-dotenv)
  - Set up frontend dependencies (vite, react, typescript, lucide-react)
  - Create .env.example files for both frontend and backend
  - Create .gitignore files to exclude node_modules, __pycache__, .env, and virtual environments
  - _Requirements: 15.1, 15.2, 15.6, 15.7_

- [x] 2. Create database schema and migrations
  - [x] 2.1 Create SQLAlchemy models for all database tables
    - Define Customer model with id, name, email, contact, created_at fields
    - Define Order model with id, customer_id, item_name, category, price, purchase_date, final_sale, created_at fields
    - Define ReturnPolicy model with category, window_days, exclusions, notes fields
    - Define Return model with id, order_id, customer_id, status, reason, agent_reasoning_log (JSONB), flagged_for_review, fast_tracked, created_at, updated_at fields
    - Define ReturnEvidence model with id, return_id, photo_url, claimed_issue, ai_verdict (JSONB), created_at fields
    - Define NotificationLog model with id, return_id, message, trigger_reason, sent_at fields
    - Configure relationships and foreign key constraints between models
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.10_
  
  - [x] 2.2 Create database connection and session management
    - Implement database.py with SQLAlchemy engine setup
    - Create get_db() dependency function for FastAPI route injection
    - Configure connection pooling for production use
    - Add database health check function
    - _Requirements: 15.4, 15.5_
  
  - [x] 2.3 Create database migration and seed scripts
    - Create Alembic migration script for initial schema (001_initial_schema.py)
    - Create seed script to populate 3 demo customers (Amara, Jordan, Priya)
    - Create seed script to populate 24 orders from the prototype
    - Create seed script to populate return_policy table with 6 categories
    - Add indexes on customer_id, purchase_date, and status fields
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6_

- [x] 3. Checkpoint - Database setup complete
  - Verify Supabase connection works
  - Verify all tables are created with correct schema
  - Verify seed data is inserted correctly
  - Ensure all tests pass, ask the user if questions arise

- [x] 4. Implement backend configuration and environment management
  - [x] 4.1 Create config.py for environment variables
    - Load ANTHROPIC_API_KEY from environment
    - Load DATABASE_URL from environment
    - Load SUPABASE_URL and SUPABASE_KEY from environment
    - Load NOTIFICATION_SERVICE_URL from environment
    - Load CORS_ORIGINS from environment (comma-separated list)
    - Validate all required environment variables on startup
    - _Requirements: 1.1, 1.5, 15.4, 15.6_
  
  - [x] 4.2 Create FastAPI main application with CORS and health check
    - Create main.py with FastAPI app instance
    - Configure CORS middleware with allowed origins from config
    - Implement GET /api/health endpoint returning status, database connection state, timestamp
    - Add global exception handlers for unhandled errors and validation errors
    - _Requirements: 5.9, 15.5, 16.1, 16.2_

- [ ] 5. Implement backend tool functions (services/tools.py)
  - [ ] 5.1 Implement search_orders tool
    - Accept customer_id and query parameters
    - Query orders table filtered by customer_id
    - Implement text matching logic for item_name and category
    - Implement date heuristics for "last week", "yesterday", "this month"
    - Return list of OrderMatch objects with order_id, item_name, category, price, purchase_date, days_since_purchase
    - Handle database errors with proper exception handling
    - _Requirements: 5.2, 4.2, 4.4, 16.3_
  
  - [ ] 5.2 Implement check_policy tool
    - Accept order_id parameter
    - Join orders and return_policy tables
    - Calculate days_since_purchase
    - Determine eligibility based on final_sale flag and return window
    - Return PolicyCheckResponse with eligible, reason, category, window_days, days_since_purchase, exclusions
    - Handle order not found errors
    - _Requirements: 5.3, 4.2, 4.4_
  
  - [ ] 5.3 Implement initiate_return tool
    - Accept order_id, reason, customer_id parameters
    - Check for existing return records for the same order
    - Generate new return_id in RET-NNNN format
    - Insert return record with status="initiated"
    - Store reason in return record
    - Return ReturnResponse with return_id, status, label_reference
    - _Requirements: 5.4, 2.8, 13.1_
  
  - [ ] 5.4 Implement verify_damage_photo tool
    - Accept return_id, consistent, confidence, notes parameters
    - Update return record with ai_verdict JSON
    - Set fast_tracked=true if consistent=true and confidence="high"
    - Set flagged_for_review=true if confidence is low or inconsistent
    - Update return_evidence table with ai_verdict
    - Return routing decision (fast_track or human_review)
    - _Requirements: 5.5, 12.2, 12.5_

- [ ] 6. Implement Claude API integration and agent orchestration loop
  - [ ] 6.1 Create agent_loop.py service for Claude tool-use orchestration
    - Implement async call_claude_api() function with proper headers and API key
    - Build system prompt template with customer context
    - Implement agent_turn() function that manages the tool-use loop
    - Accept customer_id, message, conversation_history, optional image_base64 parameters
    - Initialize conversation with user message (including image if provided)
    - Loop up to 6 iterations calling Claude API
    - Extract tool_use blocks from Claude response
    - Execute tools using the tools.py implementations
    - Append tool results back to conversation history
    - Build reasoning_trace list with tool names, inputs, and results
    - Return final text response, reasoning_trace, and iteration count
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 10.1, 10.4_
  
  - [ ] 6.2 Implement Claude API error handling
    - Handle httpx.TimeoutException with 504 status
    - Handle httpx.HTTPStatusError with appropriate error codes
    - Handle 429 rate limit errors with retry suggestion
    - Log all API errors for debugging
    - _Requirements: 16.1, 16.3_

- [ ] 7. Implement notification service integration
  - [ ] 7.1 Create notifications.py service
    - Implement send_notification() function accepting return_id, message, trigger_reason
    - Integrate with viaSocket/Twilio/SendGrid using NOTIFICATION_SERVICE_URL
    - Log notification to notifications_log table
    - Handle notification failures gracefully without blocking return processing
    - _Requirements: 7.1, 7.6, 7.7_
  
  - [ ] 7.2 Add notification triggers for return lifecycle events
    - Trigger notification when status changes to "initiated"
    - Trigger notification when status changes to "refunded"
    - Trigger notification when return is flagged for human review
    - _Requirements: 7.2, 7.3, 7.4_

- [ ] 8. Checkpoint - Backend core services complete
  - Verify tool implementations work with test data
  - Verify Claude API integration works
  - Verify notification service works
  - Ensure all tests pass, ask the user if questions arise

- [ ] 9. Implement backend API endpoints (routers)
  - [ ] 9.1 Create agent router (routers/agent.py)
    - Implement POST /api/agent/message endpoint
    - Accept AgentMessageRequest schema (customer_id, message, image_base64, conversation_history)
    - Call agent_turn() from agent_loop service
    - Return AgentMessageResponse schema (response, reasoning_trace, iterations)
    - Handle multipart/form-data for image uploads
    - _Requirements: 5.1, 3.7, 1.3, 1.4_
  
  - [ ] 9.2 Create orders router (routers/orders.py)
    - Implement GET /api/orders/search endpoint
    - Accept customer_id and query parameters
    - Call search_orders tool with parameters
    - Return list of OrderMatch objects
    - _Requirements: 5.2, 4.4_
  
  - [ ] 9.3 Create policy router (routers/policy.py)
    - Implement GET /api/policy/check endpoint
    - Accept order_id parameter
    - Call check_policy tool
    - Return PolicyCheckResponse
    - _Requirements: 5.3_
  
  - [ ] 9.4 Create returns router (routers/returns.py)
    - Implement POST /api/returns/initiate endpoint
    - Implement GET /api/returns/:id endpoint
    - Implement POST /api/returns/:id/advance endpoint for status transitions
    - Implement POST /api/returns/:id/review endpoint for human review approval/decline
    - Implement POST /api/returns/verify-photo endpoint for photo upload and AI analysis
    - Handle photo upload to Supabase Storage
    - Update return status based on actions
    - Trigger notifications on status changes
    - _Requirements: 5.4, 5.5, 5.6, 12.1, 12.3, 12.4, 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_
  
  - [ ] 9.5 Create dashboard router (routers/dashboard.py)
    - Implement GET /api/dashboard/returns endpoint
    - Query returns table with joins to orders and customers
    - Return all return records without customer_id filtering (business-wide view)
    - Include return_id, customer name, item name, reason, status, ai_verdict, flagged_for_review, created_at
    - _Requirements: 5.7, 4.5, 11.1, 11.4_

- [ ] 10. Implement Supabase Storage integration for photo uploads
  - [ ] 10.1 Create storage service for photo uploads
    - Implement upload_photo() function accepting file bytes and return_id
    - Upload to Supabase Storage returns-evidence bucket
    - Configure bucket with public read policy
    - Return public URL for uploaded photo
    - _Requirements: 6.3, 6.4, 6.7_
  
  - [ ] 10.2 Integrate photo upload with verify-photo endpoint
    - Accept multipart/form-data with return_id, photo, claimed_issue
    - Upload photo to Supabase Storage
    - Convert photo to base64 for Claude API
    - Pass base64 image to Claude for AI analysis
    - Store photo URL and AI verdict in return_evidence table
    - _Requirements: 6.1, 6.2, 6.5, 6.6_

- [ ] 11. Implement Pydantic schemas for request/response validation
  - [ ] 11.1 Create schemas.py with all request/response models
    - Define AgentMessageRequest and AgentMessageResponse
    - Define OrderMatch schema
    - Define PolicyCheckResponse schema
    - Define ReturnInitiateRequest and ReturnResponse
    - Define ReturnAdvanceRequest schema
    - Define ReturnReviewRequest schema
    - All schemas should include proper field validation and types
    - _Requirements: 5.8, 1.4_

- [ ] 12. Checkpoint - Backend API complete
  - Verify all endpoints return correct responses
  - Verify error handling works properly
  - Verify photo uploads work
  - Ensure all tests pass, ask the user if questions arise

- [ ] 13. Create frontend API client module
  - [ ] 13.1 Create api.ts with typed API client functions
    - Implement sendMessage() function calling POST /api/agent/message
    - Implement searchOrders() function calling GET /api/orders/search
    - Implement checkPolicy() function calling GET /api/policy/check
    - Implement initiateReturn() function calling POST /api/returns/initiate
    - Implement getReturn() function calling GET /api/returns/:id
    - Implement advanceReturn() function calling POST /api/returns/:id/advance
    - Implement reviewReturn() function calling POST /api/returns/:id/review
    - Implement verifyPhoto() function calling POST /api/returns/verify-photo
    - Implement getDashboardReturns() function calling GET /api/dashboard/returns
    - Configure API_BASE_URL from environment variable (VITE_API_BASE_URL)
    - Implement error handling for network failures and API errors
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 14.5, 16.4, 16.5, 16.6_

- [ ] 14. Migrate frontend to use backend API
  - [ ] 14.1 Replace direct Claude API calls in App.jsx
    - Remove callClaude() function and ANTHROPIC_API_KEY reference
    - Replace callClaude() with api.sendMessage() in sendMessage() function
    - Update conversation state management to work with backend responses
    - Extract reasoning_trace from backend response and update trace state
    - Remove local tool execution functions (execTool, search_orders, check_policy, etc.)
    - _Requirements: 1.2, 1.3, 14.5_
  
  - [ ] 14.2 Update photo upload to use backend endpoint
    - Modify handleFile() to convert image to base64
    - Update sendMessage() to include image_base64 in request payload
    - Handle multipart/form-data submission for photo uploads
    - _Requirements: 6.1, 6.2_
  
  - [ ] 14.3 Update dashboard to fetch data from backend
    - Replace local dbRef.current.returns with API call to GET /api/dashboard/returns
    - Implement polling every 5 seconds or use webhooks for real-time updates
    - Update advanceStatus() to call POST /api/returns/:id/advance
    - Update resolveReview() to call POST /api/returns/:id/review
    - _Requirements: 11.1, 11.3, 11.4, 12.1, 13.1_
  
  - [ ] 14.4 Update error handling and loading states
    - Display loading spinner during API requests
    - Display error messages in chat interface for API failures
    - Display toast notifications for dashboard action errors
    - Display retry button for network failures
    - _Requirements: 16.4, 16.5, 16.6_

- [ ] 15. Preserve UI components and styling
  - [ ] 15.1 Verify all UI components remain unchanged
    - Verify LoginScreen component layout and styling preserved
    - Verify ChatView component layout and styling preserved
    - Verify Dashboard component layout and styling preserved
    - Verify StatusPill component displays correctly
    - Verify TraceStep component displays correctly
    - Verify photo upload button and image preview preserved
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.6, 14.7_

- [ ] 16. Configure environment variables for deployment
  - [ ] 16.1 Create backend .env file with production variables
    - Add DATABASE_URL for Supabase PostgreSQL connection
    - Add ANTHROPIC_API_KEY for Claude API
    - Add SUPABASE_URL and SUPABASE_KEY for Storage
    - Add NOTIFICATION_SERVICE_URL for notification integration
    - Add CORS_ORIGINS for frontend URL whitelist
    - _Requirements: 15.4, 15.6_
  
  - [ ] 16.2 Create frontend .env file with production variables
    - Add VITE_API_BASE_URL for backend API endpoint
    - _Requirements: 15.6_

- [ ] 17. Create deployment configuration files
  - [ ] 17.1 Create Vercel configuration for frontend
    - Create vercel.json with build settings
    - Configure build command (npm run build)
    - Configure output directory (dist)
    - Configure environment variables
    - _Requirements: 15.1_
  
  - [ ] 17.2 Create Render configuration for backend
    - Create render.yaml with service configuration
    - Configure health check path (/api/health)
    - Configure environment variables
    - Configure auto-deploy on push
    - _Requirements: 15.2, 15.5_

- [ ] 18. Final checkpoint - End-to-end testing
  - Test complete customer return flow from frontend to backend
  - Test photo upload and AI verification flow
  - Test dashboard operations (advance status, review returns)
  - Test multi-user support with different customer logins
  - Verify error handling displays correctly
  - Verify notifications are sent at correct times
  - Ensure all tests pass, ask the user if questions arise

## Notes

- This migration preserves the exact UI/UX of the prototype while moving all business logic to the backend
- The agent orchestration loop now runs server-side, eliminating exposed API keys
- All data persists in Supabase PostgreSQL, enabling multi-user support and session continuity
- The frontend becomes a thin client that only handles UI rendering and user input
- Task list focuses exclusively on coding tasks; deployment will be manual using Vercel and Render dashboards
- Checkpoints ensure incremental validation at major milestones
- Each task references specific requirements for traceability

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1"] },
    { "id": 1, "tasks": ["2.1", "2.2", "4.1"] },
    { "id": 2, "tasks": ["2.3", "4.2"] },
    { "id": 3, "tasks": ["5.1", "5.2", "5.3", "5.4", "11.1"] },
    { "id": 4, "tasks": ["6.1", "7.1"] },
    { "id": 5, "tasks": ["6.2", "7.2"] },
    { "id": 6, "tasks": ["9.1", "9.2", "9.3", "10.1"] },
    { "id": 7, "tasks": ["9.4", "9.5", "10.2"] },
    { "id": 8, "tasks": ["13.1"] },
    { "id": 9, "tasks": ["14.1", "14.2", "14.3", "14.4"] },
    { "id": 10, "tasks": ["15.1", "16.1", "16.2"] },
    { "id": 11, "tasks": ["17.1", "17.2"] }
  ]
}
```
