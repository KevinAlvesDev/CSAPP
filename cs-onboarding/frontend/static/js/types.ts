/**
 * Tipos compartilhados do CS Onboarding.
 *
 * Define interfaces e types usados em todo o frontend.
 * Este arquivo serve como "single source of truth" para contratos de API.
 */

// ──────────────────────────────────────────────
// API & HTTP
// ──────────────────────────────────────────────

export interface ApiRequestOptions extends RequestInit {
    showProgress?: boolean;
    showErrorToast?: boolean;
    timeout?: number;
}

export interface ApiResponse<T = unknown> {
    data: T;
    status: number;
    ok: boolean;
    message?: string;
}

export interface ApiError {
    message: string;
    status?: number;
    details?: Record<string, unknown>;
}

// ──────────────────────────────────────────────
// Progress Bar
// ──────────────────────────────────────────────

export interface ProgressBar {
    start(): void;
    done(): void;
    set(value: number): void;
}

// ──────────────────────────────────────────────
// Notifier
// ──────────────────────────────────────────────

export interface Notifier {
    success(message: string): void;
    error(message: string): void;
    warning(message: string): void;
    info(message: string): void;
}

// ──────────────────────────────────────────────
// Domain: Implantação
// ──────────────────────────────────────────────

export interface Implantacao {
    id: number;
    codigo: string;
    empresa: string;
    status: string;
    usuario_cs: string;
    data_criacao: string;
    data_inicio?: string;
    data_finalizacao?: string;
    progresso?: number;
    nivel_atendimento?: string;
}

export interface ImplantacaoListItem extends Implantacao {
    usuario_nome?: string;
    dias_em_andamento?: number;
    total_tarefas?: number;
    tarefas_concluidas?: number;
}

// ──────────────────────────────────────────────
// Domain: Checklist
// ──────────────────────────────────────────────

export type ChecklistItemType = 'fase' | 'grupo' | 'tarefa' | 'subtarefa';

export interface ChecklistItem {
    id: number;
    parent_id: number | null;
    title: string;
    tipo_item: ChecklistItemType;
    completed: boolean;
    tag?: string;
    ordem: number;
    responsavel?: string;
    prazo_inicio?: string;
    prazo_fim?: string;
    implantacao_id: number;
}

export interface Comentario {
    id: number;
    item_id: number;
    autor: string;
    texto: string;
    created_at: string;
    tag?: string;
    editado: boolean;
    editado_em?: string;
    autor_nome?: string;
    autor_foto?: string;
}

// ──────────────────────────────────────────────
// Domain: Dashboard
// ──────────────────────────────────────────────

export interface DashboardData {
    implantacoes: ImplantacaoListItem[];
    total: number;
    page: number;
    per_page: number;
    total_pages: number;
    stats?: DashboardStats;
}

export interface DashboardStats {
    total: number;
    em_andamento: number;
    paradas: number;
    finalizadas: number;
    canceladas: number;
}

// ──────────────────────────────────────────────
// Domain: Perfil
// ──────────────────────────────────────────────

export type PerfilAcesso = 'Admin' | 'Gestor' | 'Coordenador' | 'Implantador';

export interface UserProfile {
    usuario: string;
    nome?: string;
    perfil_acesso: PerfilAcesso;
    cargo?: string;
    foto_url?: string;
}

// ──────────────────────────────────────────────
// Domain: Plano de Sucesso
// ──────────────────────────────────────────────

export interface PlanoSucesso {
    id: number;
    implantacao_id: number;
    titulo: string;
    descricao?: string;
    contexto?: string;
    created_at: string;
    acoes?: PlanoSucessoAcao[];
}

export interface PlanoSucessoAcao {
    id: number;
    plano_id: number;
    descricao: string;
    responsavel?: string;
    prazo?: string;
    concluida: boolean;
}

// ──────────────────────────────────────────────
// Config
// ──────────────────────────────────────────────

export interface Tag {
    id: number;
    nome: string;
    icone: string;
    cor_badge: string;
    ordem: number;
    tipo: string;
}

export interface StatusImplantacao {
    id: number;
    codigo: string;
    nome: string;
    cor: string;
    ordem: number;
}

// ──────────────────────────────────────────────
// Window globals (para compat com código legado)
// ──────────────────────────────────────────────

declare global {
    interface Window {
        ApiService: typeof import('./services/api-service').ApiServiceClass;
        apiFetch: (url: string, options?: RequestInit) => Promise<Response>;
        csrfToken?: string;
        showToast?: (message: string, type?: string) => void;
    }
}
