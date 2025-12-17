import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [tailwindcss(),
  svelte()],

  preview: {
    host: '0.0.0.0' // Use this if you are using the build/preview flow
  }
})
