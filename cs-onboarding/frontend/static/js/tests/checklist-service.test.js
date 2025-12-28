/**
 * Testes para ChecklistService
 * 
 * Valida lógica de negócio, validações e orquestração de API calls
 */

// Inicializa test runner
const runner = new TestRunner();
const { describe, test, testAsync, expect, fn } = {
    describe: runner.describe.bind(runner),
    test: runner.test.bind(runner),
    testAsync: runner.testAsync.bind(runner),
    expect: runner.expect.bind(runner),
    fn: runner.fn.bind(runner)
};

// ========================================
// TESTES DE VALIDAÇÃO
// ========================================

describe('ChecklistService - Validations', () => {
    let service;
    let mockAPI;
    let mockNotifier;

    // Setup
    mockAPI = {};
    mockNotifier = {
        warning: fn(),
        success: fn(),
        error: fn(),
        confirm: fn()
    };
    service = new ChecklistService(mockAPI, mockNotifier);

    test('validateCommentText should reject empty text', () => {
        const result = service.validateCommentText('');

        expect(result).toBe(false);
        expect(mockNotifier.warning.called).toBeTruthy();
    });

    test('validateCommentText should reject whitespace-only text', () => {
        const result = service.validateCommentText('   ');

        expect(result).toBe(false);
    });

    test('validateCommentText should reject text longer than 5000 chars', () => {
        const longText = 'a'.repeat(5001);
        const result = service.validateCommentText(longText);

        expect(result).toBe(false);
    });

    test('validateCommentText should accept valid text', () => {
        const result = service.validateCommentText('Valid comment');

        expect(result).toBe(true);
    });

    test('validateResponsavel should reject empty name', () => {
        const result = service.validateResponsavel('');

        expect(result).toBe(false);
    });

    test('validateResponsavel should reject name longer than 200 chars', () => {
        const longName = 'a'.repeat(201);
        const result = service.validateResponsavel(longName);

        expect(result).toBe(false);
    });

    test('validateResponsavel should accept valid name', () => {
        const result = service.validateResponsavel('João Silva');

        expect(result).toBe(true);
    });

    test('validatePrevisao should reject empty date', () => {
        const result = service.validatePrevisao('');

        expect(result).toBe(false);
    });

    test('validatePrevisao should reject invalid date', () => {
        const result = service.validatePrevisao('invalid-date');

        expect(result).toBe(false);
    });

    test('validatePrevisao should accept valid date', () => {
        const result = service.validatePrevisao('2025-12-31');

        expect(result).toBe(true);
    });
});

// ========================================
// TESTES DE LÓGICA DE NEGÓCIO
// ========================================

describe('ChecklistService - Business Logic', () => {
    let service;
    let mockAPI;
    let mockNotifier;

    // Setup para cada teste
    function setup() {
        mockAPI = {
            toggleItem: fn(),
            deleteItem: fn(),
            updateResponsavel: fn(),
            updatePrevisao: fn(),
            updateTag: fn(),
            saveComment: fn(),
            deleteComment: fn(),
            sendCommentEmail: fn(),
            getComments: fn()
        };
        mockNotifier = {
            warning: fn(),
            success: fn(),
            error: fn(),
            confirm: fn()
        };
        service = new ChecklistService(mockAPI, mockNotifier);
    }

    testAsync('toggleItem should return success on API success', async () => {
        setup();
        mockAPI.toggleItem.mockResolvedValueOnce({ ok: true, progress: 50 });

        const result = await service.toggleItem(123, true);

        expect(result.success).toBe(true);
        expect(result.progress).toBe(50);
    });

    testAsync('toggleItem should return error on API failure', async () => {
        setup();
        mockAPI.toggleItem.mockResolvedValueOnce({ ok: false, error: 'API Error' });

        const result = await service.toggleItem(123, true);

        expect(result.success).toBe(false);
    });

    testAsync('deleteItem should ask for confirmation', async () => {
        setup();
        mockNotifier.confirm.mockResolvedValueOnce(false);

        const result = await service.deleteItem(123, 'Test Item');

        expect(result.cancelled).toBe(true);
        expect(mockAPI.deleteItem.called).toBeFalsy();
    });

    testAsync('deleteItem should call API when confirmed', async () => {
        setup();
        mockNotifier.confirm.mockResolvedValueOnce(true);
        mockAPI.deleteItem.mockResolvedValueOnce({ ok: true, progress: 75 });

        const result = await service.deleteItem(123, 'Test Item');

        expect(result.success).toBe(true);
        expect(result.progress).toBe(75);
        expect(mockAPI.deleteItem.called).toBeTruthy();
    });

    testAsync('updateResponsavel should validate before calling API', async () => {
        setup();

        const result = await service.updateResponsavel(123, '');

        expect(result.success).toBe(false);
        expect(mockAPI.updateResponsavel.called).toBeFalsy();
    });

    testAsync('updateResponsavel should call API with valid data', async () => {
        setup();
        mockAPI.updateResponsavel.mockResolvedValueOnce({ ok: true });

        const result = await service.updateResponsavel(123, 'João Silva');

        expect(result.success).toBe(true);
        expect(mockNotifier.success.called).toBeTruthy();
    });

    testAsync('updatePrevisao should reject if item is completed', async () => {
        setup();

        const result = await service.updatePrevisao(123, '2025-12-31', true);

        expect(result.success).toBe(false);
        expect(mockNotifier.warning.called).toBeTruthy();
        expect(mockAPI.updatePrevisao.called).toBeFalsy();
    });

    testAsync('updatePrevisao should validate date', async () => {
        setup();

        const result = await service.updatePrevisao(123, 'invalid-date', false);

        expect(result.success).toBe(false);
        expect(mockAPI.updatePrevisao.called).toBeFalsy();
    });

    testAsync('saveComment should validate text before calling API', async () => {
        setup();

        const result = await service.saveComment(123, { texto: '' });

        expect(result.success).toBe(false);
        expect(mockAPI.saveComment.called).toBeFalsy();
    });

    testAsync('saveComment should call API with valid data', async () => {
        setup();
        mockAPI.saveComment.mockResolvedValueOnce({ ok: true });

        const result = await service.saveComment(123, {
            texto: 'Valid comment',
            visibilidade: 'interno'
        });

        expect(result.success).toBe(true);
        expect(mockNotifier.success.called).toBeTruthy();
    });

    testAsync('deleteComment should ask for confirmation', async () => {
        setup();
        mockNotifier.confirm.mockResolvedValueOnce(false);

        const result = await service.deleteComment(456);

        expect(result.cancelled).toBe(true);
        expect(mockAPI.deleteComment.called).toBeFalsy();
    });

    testAsync('sendCommentEmail should ask for confirmation', async () => {
        setup();
        mockNotifier.confirm.mockResolvedValueOnce(false);

        const result = await service.sendCommentEmail(789);

        expect(result.cancelled).toBe(true);
        expect(mockAPI.sendCommentEmail.called).toBeFalsy();
    });

    testAsync('loadComments should return comentarios on success', async () => {
        setup();
        mockAPI.getComments.mockResolvedValueOnce({
            ok: true,
            comentarios: [{ id: 1, texto: 'Test' }],
            email_responsavel: 'test@example.com'
        });

        const result = await service.loadComments(123);

        expect(result.success).toBe(true);
        expect(result.comentarios.length).toBe(1);
        expect(result.emailResponsavel).toBe('test@example.com');
    });
});

// Executa testes e mostra resultados
runner.printResults();
