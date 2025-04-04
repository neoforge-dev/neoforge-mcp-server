// Complex ES6 Import/Export Patterns

// 1. Basic imports
import React from "react";
import { useState, useEffect } from "react";
import * as ReactDOM from "react-dom";

// 2. Complex imports with aliases
import {
  Component as ReactComponent,
  PureComponent,
  memo as memoize,
} from "react";
import defaultExport, { named1, named2 as alias2 } from "module-name";
import defaultExport2, * as name from "module-name2";

// 3. Dynamic imports
const lazyComponent = () => import("./LazyComponent");
const { default: DefaultComponent } = await import("./component");

// 4. Import with side effects only
import "module-name";

// 5. Import with complex paths
import Api from "@services/api/endpoints";
import { formatDate } from "../../../utils/formatters";

// 6. Basic exports
export const API_URL = "https://api.example.com";
export function fetchData() {
  return fetch(API_URL);
}
export class DataService {
  static get() {
    return new DataService();
  }
}

// 7. Default exports (just using one default export for this test file)
export default class MainComponent {}

// For testing multiple default export types (in separate files)
// This would be in another file:
const App = () => <div>App</div>;
// export default App;

// This would also be in another file:
const objectExport = { key: "value", method() {} };
// export default objectExport;

// 8. Named exports
export { fetchData, DataService, API_URL as ApiEndpoint };

// 9. Re-exporting
export * from "./utils";
export { default as CustomButton } from "./Button";
export { Button, TextField } from "./components";
export { TextField as Input } from "./form-components";

// 10. Aggregating modules
export * from "./Button";
export * from "./TextField";
export * from "./Checkbox";
export { default as ButtonComponent } from "./Button";
export { default as TextFieldComponent } from "./TextField";
export { default as CheckboxComponent } from "./Checkbox";

// 11. Dynamic property exports
const dynamicExports = { foo: "bar", baz: 42 };
export const { foo, baz } = dynamicExports;

// 12. Async function exports
export async function fetchAsync() {
  return await fetch("https://api.example.com");
}

// 13. Generator function exports
export function* generator() {
  yield 1;
  yield 2;
}

// 14. Combined complex patterns
export { helpers } from "./components/Button";
export { CheckboxGroup, CheckboxProps } from "./components/Checkbox";
