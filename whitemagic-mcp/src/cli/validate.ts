/**
 * Configuration Validation
 * Validates API keys and tests connection to WhiteMagic API
 */

import axios from 'axios';

/**
 * Validate API key format
 */
export function validateApiKeyFormat(apiKey: string): boolean {
  // WhiteMagic API keys should be at least 32 characters
  if (!apiKey || apiKey.length < 10) {
    return false;
  }

  // Basic format check (alphanumeric with optional dashes/underscores)
  const validPattern = /^[a-zA-Z0-9_-]+$/;
  return validPattern.test(apiKey);
}

/**
 * Test connection to WhiteMagic API
 */
export async function testConnection(
  apiKey: string,
  baseUrl: string = 'https://api.whitemagic.dev'
): Promise<{ success: boolean; message: string; version?: string }> {
  try {
    // Try health endpoint first (no auth)
    const healthResponse = await axios.get(`${baseUrl}/health`, {
      timeout: 5000
    });

    if (healthResponse.status !== 200) {
      return {
        success: false,
        message: `API health check failed: ${healthResponse.status}`
      };
    }

    const version = healthResponse.data?.version || 'unknown';

    // Try authenticated endpoint
    const meResponse = await axios.get(`${baseUrl}/api/v1/users/me`, {
      headers: {
        'X-API-Key': apiKey
      },
      timeout: 5000
    });

    if (meResponse.status === 200) {
      return {
        success: true,
        message: 'Connection successful! ✅',
        version
      };
    }

    return {
      success: false,
      message: `Authentication failed: ${meResponse.status}`
    };

  } catch (error: any) {
    if (error.response) {
      // API returned an error
      if (error.response.status === 401) {
        return {
          success: false,
          message: 'Invalid API key (401 Unauthorized)'
        };
      }
      return {
        success: false,
        message: `API error: ${error.response.status} - ${error.response.statusText}`
      };
    }

    if (error.code === 'ECONNREFUSED') {
      return {
        success: false,
        message: 'Could not connect to API (connection refused)'
      };
    }

    if (error.code === 'ETIMEDOUT') {
      return {
        success: false,
        message: 'Connection timed out'
      };
    }

    return {
      success: false,
      message: `Connection error: ${error.message}`
    };
  }
}

/**
 * Validate base path
 */
export function validateBasePath(basePath: string): boolean {
  // Just check it's not empty and doesn't have invalid characters
  if (!basePath || basePath.trim().length === 0) {
    return false;
  }

  // Basic path validation (no special chars except /, -, _, .)
  const validPattern = /^[a-zA-Z0-9/_.-]+$/;
  return validPattern.test(basePath);
}
