// Em: src/pages/Login.jsx

export default function LoginPage() {

  // O seu back-end Flask (API) está (provavelmente) a rodar em http://localhost:5000
  // Esta função redireciona o utilizador para a rota /login da API,
  // que por sua vez o redireciona para o Auth0.
  const handleLogin = () => {
    // Certifique-se de que o URL do seu back-end está correto!
    window.location.href = 'http://localhost:5000/login';
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-100 dark:bg-gray-900">
      <div className="rounded-lg bg-white p-8 shadow-xl dark:bg-gray-800">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          CS Onboarding
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Por favor, faça login para continuar.
        </p>
        <button
          onClick={handleLogin}
          className="mt-6 w-full rounded-md bg-blue-600 px-4 py-2 font-semibold text-white transition hover:bg-blue-700"
        >
          Entrar ou Registrar
        </button>
      </div>
    </div>
  );
}