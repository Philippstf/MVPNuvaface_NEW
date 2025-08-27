// Firebase configuration for NuvaFace MVP
// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyD8K7rPDsYPJRKeMVZHHG6-SCihkArmipg",
  authDomain: "nuvafacemvp.firebaseapp.com",
  projectId: "nuvafacemvp",
  storageBucket: "nuvafacemvp.firebasestorage.app",
  messagingSenderId: "212268956806",
  appId: "1:212268956806:web:1694a1e93b6412551a2507",
  measurementId: "G-8S3B1YDPV6"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);

export { app, analytics };