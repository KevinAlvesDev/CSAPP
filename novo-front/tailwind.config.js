/** @type {import('tailwindcss').Config} */
export default {
  // 1. ADICIONE O 'darkMode'
  darkMode: 'class', // Isto permite o Dark Mode manual
  
  // 2. CONFIGURE O 'content'
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}", // Diz ao Tailwind para analisar todos os seus componentes
  ],

  theme: {
    extend: {},
  },
  plugins: [],
}