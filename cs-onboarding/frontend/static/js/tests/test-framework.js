/**
 * Simple Test Framework - Vanilla JavaScript
 * 
 * Sistema de testes leve sem dependências externas
 * Inspirado em Jest mas usando apenas JavaScript puro
 */

class TestRunner {
    constructor() {
        this.tests = [];
        this.results = {
            passed: 0,
            failed: 0,
            total: 0
        };
    }

    describe(suiteName, callback) {
        console.log(`\n📦 ${suiteName}`);
        callback();
    }

    test(testName, callback) {
        this.results.total++;
        try {
            callback();
            this.results.passed++;
            console.log(`  ✅ ${testName}`);
        } catch (error) {
            this.results.failed++;
            console.error(`  ❌ ${testName}`);
            console.error(`     ${error.message}`);
        }
    }

    async testAsync(testName, callback) {
        this.results.total++;
        try {
            await callback();
            this.results.passed++;
            console.log(`  ✅ ${testName}`);
        } catch (error) {
            this.results.failed++;
            console.error(`  ❌ ${testName}`);
            console.error(`     ${error.message}`);
        }
    }

    expect(actual) {
        return {
            toBe(expected) {
                if (actual !== expected) {
                    throw new Error(`Expected ${expected} but got ${actual}`);
                }
            },
            toEqual(expected) {
                if (JSON.stringify(actual) !== JSON.stringify(expected)) {
                    throw new Error(`Expected ${JSON.stringify(expected)} but got ${JSON.stringify(actual)}`);
                }
            },
            toBeTruthy() {
                if (!actual) {
                    throw new Error(`Expected truthy value but got ${actual}`);
                }
            },
            toBeFalsy() {
                if (actual) {
                    throw new Error(`Expected falsy value but got ${actual}`);
                }
            },
            toContain(item) {
                if (!actual.includes(item)) {
                    throw new Error(`Expected array to contain ${item}`);
                }
            },
            toHaveBeenCalled() {
                if (!actual.called) {
                    throw new Error('Expected function to have been called');
                }
            },
            toHaveBeenCalledWith(...args) {
                if (!actual.called) {
                    throw new Error('Expected function to have been called');
                }
                if (JSON.stringify(actual.lastArgs) !== JSON.stringify(args)) {
                    throw new Error(`Expected to be called with ${JSON.stringify(args)} but was called with ${JSON.stringify(actual.lastArgs)}`);
                }
            }
        };
    }

    fn(implementation) {
        const mock = function (...args) {
            mock.called = true;
            mock.callCount++;
            mock.lastArgs = args;

            // Retorna valor mockado se definido
            if (mock.mockReturnValue !== undefined) {
                return mock.mockReturnValue;
            }

            // Retorna promise resolvida se definido
            if (mock.mockResolvedValue !== undefined) {
                return Promise.resolve(mock.mockResolvedValue);
            }

            // Retorna promise rejeitada se definido
            if (mock.mockRejectedValue !== undefined) {
                return Promise.reject(mock.mockRejectedValue);
            }

            // Executa implementação se fornecida
            if (implementation) {
                return implementation(...args);
            }
        };

        mock.called = false;
        mock.callCount = 0;
        mock.lastArgs = null;
        mock.mockReturnValue = undefined;
        mock.mockResolvedValue = undefined;
        mock.mockRejectedValue = undefined;

        mock.mockReturnValueOnce = (value) => {
            mock.mockReturnValue = value;
            return mock;
        };

        mock.mockResolvedValueOnce = (value) => {
            mock.mockResolvedValue = value;
            return mock;
        };

        mock.mockRejectedValueOnce = (value) => {
            mock.mockRejectedValue = value;
            return mock;
        };

        return mock;
    }

    printResults() {
        console.log(`\n${'='.repeat(50)}`);
        console.log(`📊 Test Results:`);
        console.log(`   Total: ${this.results.total}`);
        console.log(`   ✅ Passed: ${this.results.passed}`);
        console.log(`   ❌ Failed: ${this.results.failed}`);
        console.log(`   Coverage: ${Math.round((this.results.passed / this.results.total) * 100)}%`);
        console.log(`${'='.repeat(50)}\n`);

        if (this.results.failed === 0) {
            console.log('🎉 All tests passed!');
        } else {
            console.log(`⚠️  ${this.results.failed} test(s) failed`);
        }
    }
}

// Export para uso global
if (typeof window !== 'undefined') {
    window.TestRunner = TestRunner;
}
