/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Light Theme
        sidebarLight:"#B0DB9C",  //"#ffffffff",//
        sidebarTextLight: "#016B61",
        bgLight: "#ECFAE5",
        navButtonLight: "#DDF6D2",
        navButtonHoverLight: "#66f29eff",
        navButtonBorderLight: "#ECFAE5",
        navTextLight: "#424642",

        // Dark Theme
        sidebarDark: "#222831",
        sidebarTextDark: "#00ADB5",
        bgDark: "#31363F",
        navButtonDark: "#31363F",
        navButtonHoverDark: "#387bbdff",
        navButtonBorderDark: "#3C3D37",
        navTextDark: "#ECDFCC",
        accentDark: "#00ADB5",

        // General
        primary: "#016B61",
      },
      width: {
        sidebarwidth:'17%',
        mainwidth:'83%',
        onethird:'30%',
      },
     
    },
  },
  plugins: [],
}
