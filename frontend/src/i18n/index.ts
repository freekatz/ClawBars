import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import en from './locales/en.json';
import zh from './locales/zh.json';

const LANG_KEY = 'clawbars_lang';

const resources = {
  en: { translation: en },
  zh: { translation: zh },
};

const savedLang = localStorage.getItem(LANG_KEY) as 'en' | 'zh' | null;
const browserLang = navigator.language?.startsWith('zh') ? 'zh' : 'en';
const initialLang = savedLang || browserLang;

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: initialLang,
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false,
    },
  });

i18n.on('languageChanged', (lng) => {
  localStorage.setItem(LANG_KEY, lng);
});

export default i18n;
