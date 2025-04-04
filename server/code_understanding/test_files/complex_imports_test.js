// Default imports
import React from 'react';
import ReactDOM from 'react-dom';

// Named imports
import { useState, useEffect } from 'react';
import { createStore, combineReducers as combine } from 'redux';

// Namespace imports
import * as Yup from 'yup';

// Side-effect imports (just to execute code)
import 'core-js/stable';
import 'regenerator-runtime/runtime';

// Complex path imports
import apiClient from '@services/api/client';
import { formatDate } from '../../../utils/formatters';

// Dynamic imports (these won't be detected at parse time)
// const SomeComponent = React.lazy(() => import('./SomeComponent'));

// Default export of a function
export default function App() {
  return <div>Hello World</div>;
}

// Named exports
export const BASE_URL = 'https://api.example.com';
export let apiVersion = 'v1';
export var DEBUG = true;

// Export with destructuring
export const { id, name } = user;

// Function exports
export function getData() {
  return fetch('/api/data');
}

// Async function exports
export async function fetchUserData(userId) {
  const response = await fetch(`/api/users/${userId}`);
  return response.json();
}

// Generator function exports
export function* generateIds() {
  let id = 1;
  while (true) {
    yield id++;
  }
}

// Class exports
export class UserService {
  constructor(apiKey) {
    this.apiKey = apiKey;
  }
  
  getUser(id) {
    return fetch(`/api/users/${id}`, {
      headers: { 'Authorization': `Bearer ${this.apiKey}` }
    });
  }
}

// Re-exports
export { default as Button } from './Button';
export { Card, CardHeader, CardBody } from './Card';

// Namespace re-exports
export * as utils from './utils';
export * from './helpers';

// Aggregated exports
const privateFunction = () => console.log('private');
const publicFunction = () => console.log('public');

export {
  publicFunction,
  UserService as default  // Re-export as default
}; 