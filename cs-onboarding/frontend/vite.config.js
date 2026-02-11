import { defineConfig } from 'vite';
import { resolve } from 'path';
import { glob } from 'glob';
import viteCompression from 'vite-plugin-compression';

/**
 * Configuração do Vite para CS Onboarding Frontend
 * 
 * Este setup permite:
 * - Minificação e bundling de JS/CSS em produção
 * - Compressão gzip e brotli
 * - Hot Module Replacement em desenvolvimento
 * - Preservar estrutura de arquivos existente
 * 
 * Uso:
 * - Desenvolvimento: npm run dev
 * - Build produção: npm run build
 * - Preview build: npm run preview
 */

// Encontrar todos os arquivos JS e TS de entrada
const jsEntries = glob.sync('static/js/**/*.{js,ts}', {
    ignore: ['static/js/dist/**', 'static/js/tests/**', 'static/js/**/*.min.js', 'static/js/**/*.d.ts'],
});

// Criar mapa de entradas para build
const input = {};
jsEntries.forEach((file) => {
    const name = file.replace('static/js/', '').replace(/\.(js|ts)$/, '');
    input[name] = resolve(__dirname, file);
});

export default defineConfig({
    root: '.',
    base: '/static/',

    build: {
        outDir: 'static/dist',
        emptyOutDir: true,
        sourcemap: false,
        minify: 'terser',

        rollupOptions: {
            input,
            output: {
                // Preservar estrutura de pastas
                entryFileNames: 'js/[name].min.js',
                chunkFileNames: 'js/chunks/[name]-[hash].js',
                assetFileNames: (assetInfo) => {
                    if (assetInfo.name?.endsWith('.css')) {
                        return 'css/[name].min[extname]';
                    }
                    return 'assets/[name]-[hash][extname]';
                },
            },
        },

        terserOptions: {
            compress: {
                drop_console: true,
                drop_debugger: true,
                pure_funcs: ['console.log', 'console.debug'],
            },
            mangle: {
                safari10: true,
            },
            format: {
                comments: false,
            },
        },
    },

    plugins: [
        // Compressão gzip
        viteCompression({
            algorithm: 'gzip',
            ext: '.gz',
            threshold: 1024, // Só comprime arquivos > 1KB
        }),
        // Compressão brotli
        viteCompression({
            algorithm: 'brotliCompress',
            ext: '.br',
            threshold: 1024,
        }),
    ],

    server: {
        // Proxy para o backend Flask em desenvolvimento
        proxy: {
            '/api': {
                target: 'http://localhost:5000',
                changeOrigin: true,
            },
            '/auth': {
                target: 'http://localhost:5000',
                changeOrigin: true,
            },
        },
        // Open browser on start
        open: false,
        port: 3000,
    },

    // Otimizações de dependências
    optimizeDeps: {
        include: [],
        exclude: [],
    },
});
