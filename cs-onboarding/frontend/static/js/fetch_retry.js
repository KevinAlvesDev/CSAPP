/**
 * Fetch with Automatic Retry
 * 
 * Utility function to retry failed fetch requests with exponential backoff.
 * Useful for external API calls that may fail temporarily (network issues, timeouts, etc.)
 * 
 * @param {string} url - URL to fetch
 * @param {object} options - Fetch options (method, headers, body, etc.)
 * @param {number} maxRetries - Maximum number of retry attempts (default: 3)
 * @param {number} timeoutMs - Timeout in milliseconds per attempt (default: 15000)
 * @returns {Promise<Response>} - Fetch response
 * @throws {Error} - If all retries fail
 */
async function fetchWithRetry(url, options = {}, maxRetries = 3, timeoutMs = 15000) {
    // Exponential backoff delays: 1s, 2s, 4s
    const delays = [1000, 2000, 4000];

    for (let attempt = 0; attempt < maxRetries; attempt++) {
        try {
            // Create abort controller for timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

            // Add signal to options
            const fetchOptions = {
                ...options,
                signal: controller.signal
            };

            // Attempt fetch
            const response = await fetch(url, fetchOptions);

            // Clear timeout
            clearTimeout(timeoutId);

            // Success!
            if (response.ok) {
                if (attempt > 0 && window.showToast) {
                    showToast(`✅ Sucesso na tentativa ${attempt + 1}`, 'success');
                }
                return response;
            }

            // Client error (4xx) - don't retry
            if (response.status >= 400 && response.status < 500) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            // Server error (5xx) - retry
            if (attempt < maxRetries - 1) {
                if (window.showToast) {
                    showToast(`⚠️ Erro ${response.status}. Tentativa ${attempt + 1}/${maxRetries}. Tentando novamente...`, 'warning');
                }
            }

        } catch (error) {
            const isLastAttempt = attempt === maxRetries - 1;
            const isAbortError = error.name === 'AbortError';
            const isNetworkError = error.message === 'Failed to fetch' || error.message.includes('network');

            // Log error
            console.error(`Fetch attempt ${attempt + 1} failed:`, error);

            // Last attempt - throw error
            if (isLastAttempt) {
                if (window.showToast) {
                    if (isAbortError) {
                        showToast('❌ Tempo de espera esgotado após 3 tentativas. Verifique sua conexão.', 'error');
                    } else if (isNetworkError) {
                        showToast('❌ Erro de conexão após 3 tentativas. Verifique sua internet.', 'error');
                    } else {
                        showToast(`❌ Falha após ${maxRetries} tentativas: ${error.message}`, 'error');
                    }
                }
                throw error;
            }

            // Show retry message
            if (window.showToast) {
                if (isAbortError) {
                    showToast(`⏱️ Timeout na tentativa ${attempt + 1}. Tentando novamente em ${delays[attempt] / 1000}s...`, 'warning');
                } else {
                    showToast(`⚠️ Tentativa ${attempt + 1} falhou. Tentando novamente em ${delays[attempt] / 1000}s...`, 'warning');
                }
            }

            // Wait before retry (exponential backoff)
            await new Promise(resolve => setTimeout(resolve, delays[attempt]));
        }
    }

    // Should never reach here
    throw new Error('Unexpected error in fetchWithRetry');
}

/**
 * Helper function to sleep for a specified duration
 * @param {number} ms - Milliseconds to sleep
 * @returns {Promise<void>}
 */
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { fetchWithRetry, sleep };
}
