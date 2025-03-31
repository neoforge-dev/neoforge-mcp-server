// Test imports
import { foo, bar } from "./module";
import defaultExport from "./default";

// Test requires
const express = require("express");
const path = require("path");

// Test class with methods
class TestClass {
  constructor() {
    this.value = 42;
  }

  async getValue() {
    return this.value;
  }

  static getStaticValue() {
    return 100;
  }
}

// Test function declarations
function regularFunction() {
  return "regular";
}

async function asyncFunction() {
  return "async";
}

// Test variable declarations
const constant = "constant";
let variable = "variable";

// Test exports
export const namedExport = "named";
export default class DefaultExport {
  method() {
    return "default";
  }
}
