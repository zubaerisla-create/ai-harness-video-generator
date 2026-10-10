/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        'lms-primary': '#E60000',
        'pastel-cream': '#FFF4E0',
        'pastel-mint': '#E8FFE0',
        'pastel-blue': '#E0F4FF',
        'pastel-purple': '#F0E0FF',
        'footer-bg': '#F5F5F0',
      },
      fontFamily: {
        display: ['"Bricolage Grotesque"', 'sans-serif'],
        sans: ['"Space Grotesk"', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'brutalist-sm': '2px 2px 0px 0px rgba(0,0,0,1)',
        'brutalist': '4px 4px 0px 0px rgba(0,0,0,1)',
        'brutalist-md': '6px 6px 0px 0px rgba(0,0,0,1)',
        'brutalist-lg': '8px 8px 0px 0px rgba(0,0,0,1)',
        'brutalist-xl': '12px 12px 0px 0px rgba(0,0,0,1)',
        'brutalist-2xl': '16px 16px 0px 0px rgba(0,0,0,1)',
        'brutalist-red-sm': '2px 2px 0px 0px rgba(230,0,0,1)',
        'brutalist-red': '4px 4px 0px 0px rgba(230,0,0,1)',
        'brutalist-red-md': '6px 6px 0px 0px rgba(230,0,0,1)',
        'brutalist-red-lg': '8px 8px 0px 0px rgba(230,0,0,1)',
        'brutalist-white': '4px 4px 0px 0px rgba(255,255,255,1)',
        'brutalist-white-md': '6px 6px 0px 0px rgba(255,255,255,1)',
        'brutalist-white-lg': '8px 8px 0px 0px rgba(255,255,255,1)',
        'brutalist-white-xl': '12px 12px 0px 0px rgba(255,255,255,1)',
      },
    },
  },
  plugins: [],
};
