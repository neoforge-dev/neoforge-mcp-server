// Basic interfaces - essential for type definitions
interface User {
    id: number;
    name: string;
    email?: string;  // Optional property
}

// Interface with methods
interface DataService {
    getData(): Promise<User[]>;
    getUser(id: number): Promise<User>;
    createUser(user: Omit<User, 'id'>): Promise<User>;
}

// Basic type aliases - commonly used for unions and primitives
type Status = 'active' | 'inactive' | 'pending';
type UserRole = 'admin' | 'user' | 'guest';

// Mapped types
type ReadonlyUser = Readonly<User>;
type PartialUser = Partial<User>;
type PickUser = Pick<User, 'id' | 'name'>;
type OmitUser = Omit<User, 'email'>;

// Basic enums - commonly used for constants
enum Direction {
    Up,
    Down,
    Left,
    Right
}

enum Color {
    Red = 'red',
    Green = 'green',
    Blue = 'blue'
}

// Generic types
interface Response<T> {
    data: T;
    status: number;
    message?: string;
}

// Function type annotations - essential for type safety
function processUser(user: User): Promise<User> {
    return Promise.resolve(user);
}

// Arrow function with type annotations
const formatUser = (user: User): string => {
    return `${user.name} (${user.id})`;
};

// Class with type annotations
class UserManager {
    private users: User[] = [];
    
    constructor(private readonly service: any) {}
    
    async addUser(user: User): Promise<User> {
        this.users.push(user);
        return user;
    }
    
    getUserById(id: number): User | undefined {
        return this.users.find(user => user.id === id);
    }
}

// Type assertions
const userData = {
    id: 1,
    name: 'John Doe'
} as User;

// Type guards
function isUser(obj: any): obj is User {
    return obj && typeof obj.id === 'number' && typeof obj.name === 'string';
}

// Variable type annotations
let userCount: number = 0;
const activeUsers: User[] = [];
const userMap: Map<number, User> = new Map();

// Union and intersection types
type StringOrNumber = string | number;
type AdminUser = User & { role: 'admin' };

// Function overloads
function processData(data: string): string;
function processData(data: number): number;
function processData(data: string | number): string | number {
    return data;
}

// Index signatures
interface StringMap {
    [key: string]: string;
}

// Tuple types
type UserTuple = [number, string, string?];

// Optional chaining and nullish coalescing
const user: User | null = null;
const userName = user?.name ?? 'Anonymous';

// Interface declaration
interface UserInterface {
    id: number;
    name: string;
    email: string;
    role: UserRole;
}

// Type alias
type UserType = {
    id: number;
    name: string;
    email: string;
    role: UserRole;
};

// Enum declaration
enum UserRole {
    Admin = 'ADMIN',
    User = 'USER',
    Guest = 'GUEST'
}

// Function with type annotations
function processUser(user: UserInterface): void {
    console.log(`Processing user ${user.name} with role ${user.role}`);
}

// Variable with type annotation
const testUser: UserInterface = {
    id: 1,
    name: 'John Doe',
    email: 'john@example.com',
    role: UserRole.Admin
}; 