/**
 * API Client for ReturnPilot Backend
 * Centralized API communication with error handling
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Base fetch wrapper with error handling
 */
async function apiFetch(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || `API Error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error(`API request failed: ${endpoint}`, error);
    throw error;
  }
}

export const api = {
  /**
   * Send a message to the agent
   * @param {string} customerId - Customer ID
   * @param {string} message - User message text
   * @param {string|null} imageBase64 - Optional base64-encoded image
   * @param {Array} conversationHistory - Previous conversation messages
   * @returns {Promise<{response: string, reasoning_trace: Array, iterations: number}>}
   */
  sendMessage: async (customerId, message, imageBase64 = null, conversationHistory = []) => {
    return apiFetch('/api/agent/message', {
      method: 'POST',
      body: JSON.stringify({
        customer_id: customerId,
        message,
        image_base64: imageBase64,
        conversation_history: conversationHistory,
      }),
    });
  },

  /**
   * Search for orders
   * @param {string} customerId - Customer ID
   * @param {string} query - Search query
   * @returns {Promise<{matches: Array}>}
   */
  searchOrders: async (customerId, query) => {
    const params = new URLSearchParams({ customer_id: customerId, q: query });
    return apiFetch(`/api/orders/search?${params}`);
  },

  /**
   * Check return policy for an order
   * @param {string} orderId - Order ID
   * @returns {Promise<{eligible: boolean, reason: string, ...}>}
   */
  checkPolicy: async (orderId) => {
    const params = new URLSearchParams({ order_id: orderId });
    return apiFetch(`/api/policy/check?${params}`);
  },

  /**
   * Initiate a return
   * @param {string} orderId - Order ID
   * @param {string} reason - Return reason
   * @param {string} customerId - Customer ID
   * @returns {Promise<{return_id: string, status: string, ...}>}
   */
  initiateReturn: async (orderId, reason, customerId) => {
    return apiFetch('/api/returns/initiate', {
      method: 'POST',
      body: JSON.stringify({
        order_id: orderId,
        reason,
        customer_id: customerId,
      }),
    });
  },

  /**
   * Get return details
   * @param {string} returnId - Return ID
   * @returns {Promise<{id: string, status: string, ...}>}
   */
  getReturn: async (returnId) => {
    return apiFetch(`/api/returns/${returnId}`);
  },

  /**
   * Advance return status
   * @param {string} returnId - Return ID
   * @returns {Promise<{id: string, status: string, ...}>}
   */
  advanceReturn: async (returnId) => {
    return apiFetch(`/api/returns/${returnId}/advance`, {
      method: 'POST',
      body: JSON.stringify({ action: 'advance' }),
    });
  },

  /**
   * Review a flagged return (approve or decline)
   * @param {string} returnId - Return ID
   * @param {string} action - 'approve' or 'decline'
   * @returns {Promise<{id: string, status: string, ...}>}
   */
  reviewReturn: async (returnId, action) => {
    return apiFetch(`/api/returns/${returnId}/review`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    });
  },

  /**
   * Get all returns for dashboard
   * @returns {Promise<{returns: Array}>}
   */
  getDashboardReturns: async () => {
    return apiFetch('/api/dashboard/returns');
  },

  /**
   * List all returns belonging to one customer (for the My Returns page)
   * @param {string} customerId - Customer ID
   * @returns {Promise<{returns: Array, total: number}>}
   */
  getCustomerReturns: async (customerId) => {
    return apiFetch(`/api/returns/customer/${customerId}`);
  },

  /**
   * Upload return-evidence photo and run AI consistency verification.
   * Not JSON — multipart/form-data, so this bypasses the apiFetch() wrapper.
   * @param {string} returnId - Return ID the photo is evidence for
   * @param {string} claimedIssue - Customer's stated issue
   * @param {File} photoFile - The image file
   * @returns {Promise<{success: bool, routing: string, ai_verdict: object, photo_url: string}>}
   */
  verifyPhoto: async (returnId, claimedIssue, photoFile) => {
    const form = new FormData();
    form.append('return_id', returnId);
    form.append('claimed_issue', claimedIssue);
    form.append('photo', photoFile);

    const response = await fetch(`${API_BASE_URL}/api/returns/verify-photo`, {
      method: 'POST',
      body: form,
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `API Error: ${response.status}`);
    }
    return await response.json();
  },

  /**
   * Health check
   * @returns {Promise<{status: string, timestamp: string}>}
   */
  healthCheck: async () => {
    return apiFetch('/api/health');
  },
};

export default api;
