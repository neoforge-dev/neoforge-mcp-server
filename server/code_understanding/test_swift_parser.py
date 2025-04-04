import pytest
from server.code_understanding.swift_parser import parse_swift_code

def test_swift_imports():
    code = """
    import Foundation
    import SwiftUI
    import Combine
    """
    result = parse_swift_code(code)
    assert len(result.imports) == 3
    assert result.imports[0].module == "Foundation"
    assert result.imports[1].module == "SwiftUI"
    assert result.imports[2].module == "Combine"

def test_swift_function_declaration():
    code = """
    func calculateSum(_ a: Int, _ b: Int) -> Int {
        return a + b
    }
    """
    result = parse_swift_code(code)
    assert len(result.functions) == 1
    func = result.functions[0]
    assert func.name == "calculateSum"
    assert len(func.parameters) == 2
    assert func.return_type == "Int"

def test_swift_class_declaration():
    code = """
    class Person {
        var name: String
        var age: Int
        
        init(name: String, age: Int) {
            self.name = name
            self.age = age
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.classes) == 1
    cls = result.classes[0]
    assert cls.name == "Person"
    assert len(cls.properties) == 2
    assert len(cls.methods) == 1

def test_swift_struct_declaration():
    code = """
    struct Point {
        var x: Double
        var y: Double
        
        var magnitude: Double {
            return sqrt(x * x + y * y)
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "Point"
    assert len(struct.properties) == 2
    assert len(struct.computed_properties) == 1

def test_swift_protocol_declaration():
    code = """
    protocol Identifiable {
        var id: String { get }
        func identify() -> String
    }
    """
    result = parse_swift_code(code)
    assert len(result.protocols) == 1
    protocol = result.protocols[0]
    assert protocol.name == "Identifiable"
    assert len(protocol.requirements) == 2

def test_swift_enum_declaration():
    code = """
    enum Direction {
        case north
        case south
        case east
        case west
    }
    """
    result = parse_swift_code(code)
    assert len(result.enums) == 1
    enum = result.enums[0]
    assert enum.name == "Direction"
    assert len(enum.cases) == 4

def test_swift_extension():
    code = """
    extension String {
        var isPalindrome: Bool {
            return self == String(self.reversed())
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.extensions) == 1
    extension = result.extensions[0]
    assert extension.type_name == "String"
    assert len(extension.members) == 1

def test_swift_generics():
    code = """
    struct Stack<Element> {
        var items: [Element] = []
        
        mutating func push(_ item: Element) {
            items.append(item)
        }
        
        mutating func pop() -> Element? {
            return items.popLast()
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "Stack"
    assert len(struct.generic_parameters) == 1
    assert struct.generic_parameters[0] == "Element"

def test_swift_property_wrappers():
    code = """
    struct ContentView: View {
        @State private var count = 0
        @Binding var isPresented: Bool
        @ObservedObject var viewModel: ViewModel
        @EnvironmentObject var settings: Settings
        
        var body: some View {
            Text("Count: \(count)")
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "ContentView"
    assert len(struct.properties) == 4
    assert any(p.name == "count" and p.property_wrapper == "@State" for p in struct.properties)
    assert any(p.name == "isPresented" and p.property_wrapper == "@Binding" for p in struct.properties)
    assert any(p.name == "viewModel" and p.property_wrapper == "@ObservedObject" for p in struct.properties)
    assert any(p.name == "settings" and p.property_wrapper == "@EnvironmentObject" for p in struct.properties)

def test_swift_error_handling():
    code = """
    enum NetworkError: Error {
        case invalidURL
        case requestFailed
        case invalidResponse
    }
    
    func fetchData() throws -> Data {
        guard let url = URL(string: "https://example.com") else {
            throw NetworkError.invalidURL
        }
        // Implementation
        return Data()
    }
    """
    result = parse_swift_code(code)
    assert len(result.enums) == 1
    assert len(result.functions) == 1
    func = result.functions[0]
    assert func.name == "fetchData"
    assert func.throws == True

def test_swift_async_await():
    code = """
    func fetchUserData() async throws -> User {
        let data = try await fetchData()
        return try JSONDecoder().decode(User.self, from: data)
    }
    """
    result = parse_swift_code(code)
    assert len(result.functions) == 1
    func = result.functions[0]
    assert func.name == "fetchUserData"
    assert func.async == True
    assert func.throws == True

def test_swiftui_view():
    code = """
    struct ContentView: View {
        var body: some View {
            VStack {
                Text("Hello, World!")
                    .font(.title)
                    .foregroundColor(.blue)
                
                Button("Click me") {
                    print("Button tapped")
                }
                .padding()
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "ContentView"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 1
    assert struct.properties[0].name == "body"
    assert struct.properties[0].type == "some View"

def test_swiftui_modifiers():
    code = """
    struct ModifiedView: View {
        var body: some View {
            Text("Hello")
                .font(.system(size: 20, weight: .bold))
                .foregroundColor(.blue)
                .padding()
                .background(Color.yellow)
                .cornerRadius(10)
                .shadow(radius: 5)
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "ModifiedView"
    assert struct.conforms_to == ["View"]
    view = struct.properties[0].value
    assert len(view.modifiers) == 6

def test_swiftui_state():
    code = """
    struct CounterView: View {
        @State private var count = 0
        
        var body: some View {
            VStack {
                Text("Count: \(count)")
                Button("Increment") {
                    count += 1
                }
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "CounterView"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 2
    assert struct.properties[0].name == "count"
    assert struct.properties[0].property_wrapper == "@State"

def test_swiftui_binding():
    code = """
    struct ToggleView: View {
        @Binding var isOn: Bool
        
        var body: some View {
            Toggle("Toggle", isOn: $isOn)
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "ToggleView"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 2
    assert struct.properties[0].name == "isOn"
    assert struct.properties[0].property_wrapper == "@Binding"

def test_swiftui_environment():
    code = """
    struct ThemeView: View {
        @Environment(\.colorScheme) var colorScheme
        
        var body: some View {
            Text("Theme: \(colorScheme == .dark ? "Dark" : "Light")")
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "ThemeView"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 2
    assert struct.properties[0].name == "colorScheme"
    assert struct.properties[0].property_wrapper == "@Environment"

def test_swiftui_environment_object():
    code = """
    class UserSettings: ObservableObject {
        @Published var username = ""
        @Published var isLoggedIn = false
    }
    
    struct SettingsView: View {
        @EnvironmentObject var settings: UserSettings
        
        var body: some View {
            VStack {
                TextField("Username", text: $settings.username)
                Toggle("Logged In", isOn: $settings.isLoggedIn)
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.classes) == 1
    assert len(result.structs) == 1
    settings_class = result.classes[0]
    assert settings_class.name == "UserSettings"
    assert settings_class.conforms_to == ["ObservableObject"]
    assert len(settings_class.properties) == 2
    settings_view = result.structs[0]
    assert settings_view.name == "SettingsView"
    assert settings_view.conforms_to == ["View"]
    assert len(settings_view.properties) == 2
    assert settings_view.properties[0].name == "settings"
    assert settings_view.properties[0].property_wrapper == "@EnvironmentObject"

def test_swiftui_observed_object():
    code = r"""
    class ViewModel: ObservableObject {
        @Published var items: [String] = []
    }
    
    struct ListView: View {
        @ObservedObject var viewModel: ViewModel
        
        var body: some View {
            List(viewModel.items, id: \.self) { item in
                Text(item)
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.classes) == 1
    assert len(result.structs) == 1
    view_model = result.classes[0]
    assert view_model.name == "ViewModel"
    assert view_model.conforms_to == ["ObservableObject"]
    assert len(view_model.properties) == 2
    list_view = result.structs[0]
    assert list_view.name == "ListView"
    assert list_view.conforms_to == ["View"]
    assert len(list_view.properties) == 2
    assert list_view.properties[0].name == "viewModel"
    assert list_view.properties[0].property_wrapper == "@ObservedObject"

def test_swiftui_navigation():
    code = """
    struct NavigationExample: View {
        var body: some View {
            NavigationView {
                List {
                    NavigationLink(destination: DetailView()) {
                        Text("Go to Detail")
                    }
                }
                .navigationTitle("Main View")
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "NavigationExample"
    assert struct.conforms_to == ["View"]
    view = struct.properties[0].value
    assert view.type == "NavigationView"
    assert len(view.children) == 1
    list_view = view.children[0]
    assert list_view.type == "List"
    assert len(list_view.children) == 1
    assert list_view.children[0].type == "NavigationLink"

def test_swiftui_sheets():
    code = """
    struct SheetExample: View {
        @State private var showingSheet = false
        
        var body: some View {
            Button("Show Sheet") {
                showingSheet = true
            }
            .sheet(isPresented: $showingSheet) {
                SheetView()
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "SheetExample"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 2
    assert struct.properties[0].name == "showingSheet"
    assert struct.properties[0].property_wrapper == "@State"
    button = struct.properties[1].value
    assert button.type == "Button"
    assert len(button.modifiers) == 1
    assert button.modifiers[0].name == "sheet"

def test_swiftui_alerts():
    code = """
    struct AlertExample: View {
        @State private var showingAlert = false
        
        var body: some View {
            Button("Show Alert") {
                showingAlert = true
            }
            .alert("Alert Title", isPresented: $showingAlert) {
                Button("OK", role: .cancel) { }
                Button("Delete", role: .destructive) { }
            } message: {
                Text("This is an alert message")
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "AlertExample"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 2
    assert struct.properties[0].name == "showingAlert"
    assert struct.properties[0].property_wrapper == "@State"
    button = struct.properties[1].value
    assert button.type == "Button"
    assert len(button.modifiers) == 1
    assert button.modifiers[0].name == "alert"

def test_swiftui_gestures():
    code = """
    struct GestureExample: View {
        @State private var offset = CGSize.zero
        
        var body: some View {
            Image(systemName: "star")
                .offset(offset)
                .gesture(
                    DragGesture()
                        .onChanged { gesture in
                            offset = gesture.translation
                        }
                        .onEnded { _ in
                            withAnimation {
                                offset = .zero
                            }
                        }
                )
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "GestureExample"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 2
    assert struct.properties[0].name == "offset"
    assert struct.properties[0].property_wrapper == "@State"
    image = struct.properties[1].value
    assert image.type == "Image"
    assert len(image.modifiers) == 2
    assert image.modifiers[1].name == "gesture"

def test_swiftui_animations():
    code = """
    struct AnimationExample: View {
        @State private var isAnimating = false
        
        var body: some View {
            Circle()
                .fill(isAnimating ? Color.blue : Color.red)
                .frame(width: 100, height: 100)
                .scaleEffect(isAnimating ? 1.5 : 1.0)
                .animation(.spring(), value: isAnimating)
                .onTapGesture {
                    withAnimation {
                        isAnimating.toggle()
                    }
                }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "AnimationExample"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 2
    assert struct.properties[0].name == "isAnimating"
    assert struct.properties[0].property_wrapper == "@State"
    circle = struct.properties[1].value
    assert circle.type == "Circle"
    assert len(circle.modifiers) == 5
    assert circle.modifiers[3].name == "animation"

def test_swiftui_timers():
    code = """
    struct TimerExample: View {
        @State private var timeRemaining = 60
        let timer = Timer.publish(every: 1, on: .main, in: .common).autoconnect()
        
        var body: some View {
            Text("\(timeRemaining)")
                .onReceive(timer) { _ in
                    if timeRemaining > 0 {
                        timeRemaining -= 1
                    }
                }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "TimerExample"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 3
    assert struct.properties[0].name == "timeRemaining"
    assert struct.properties[0].property_wrapper == "@State"
    assert struct.properties[1].name == "timer"
    text = struct.properties[2].value
    assert text.type == "Text"
    assert len(text.modifiers) == 1
    assert text.modifiers[0].name == "onReceive"

def test_swiftui_async_image():
    code = """
    struct AsyncImageExample: View {
        var body: some View {
            AsyncImage(url: URL(string: "https://example.com/image.jpg")) { phase in
                switch phase {
                case .empty:
                    ProgressView()
                case .success(let image):
                    image
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                case .failure:
                    Image(systemName: "photo")
                @unknown default:
                    EmptyView()
                }
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "AsyncImageExample"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 1
    async_image = struct.properties[0].value
    assert async_image.type == "AsyncImage"
    assert len(async_image.modifiers) == 0

def test_swiftui_refreshable():
    code = r"""
    struct RefreshableExample: View {
        @State private var items: [String] = []
        
        var body: some View {
            List(items, id: \.self) { item in
                Text(item)
            }
            .refreshable {
                await loadItems()
            }
        }
        
        func loadItems() async {
            // Implementation
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "RefreshableExample"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 2
    assert struct.properties[0].name == "items"
    assert struct.properties[0].property_wrapper == "@State"
    list_view = struct.properties[1].value
    assert list_view.type == "List"
    assert len(list_view.modifiers) == 1
    assert list_view.modifiers[0].name == "refreshable"

def test_swiftui_searchable():
    code = r"""
    struct SearchableExample: View {
        @State private var searchText = ""
        @State private var filteredItems: [String] = []
        
        var body: some View {
            List(filteredItems, id: \.self) { item in
                Text(item)
            }
            .searchable(text: $searchText)
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "SearchableExample"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 3
    assert struct.properties[0].name == "searchText"
    assert struct.properties[0].property_wrapper == "@State"
    assert struct.properties[1].name == "items"
    assert struct.properties[1].property_wrapper == "@State"
    list_view = struct.properties[2].value
    assert list_view.type == "List"
    assert len(list_view.modifiers) == 1
    assert list_view.modifiers[0].name == "searchable"

def test_swiftui_toolbar():
    code = """
    struct ToolbarExample: View {
        var body: some View {
            NavigationView {
                Text("Content")
                    .toolbar {
                        ToolbarItem(placement: .navigationBarLeading) {
                            Button("Menu") { }
                        }
                        ToolbarItem(placement: .navigationBarTrailing) {
                            Button("Done") { }
                        }
                    }
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "ToolbarExample"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 1
    navigation_view = struct.properties[0].value
    assert navigation_view.type == "NavigationView"
    assert len(navigation_view.children) == 1
    text = navigation_view.children[0]
    assert text.type == "Text"
    assert len(text.modifiers) == 1
    assert text.modifiers[0].name == "toolbar"

def test_swiftui_context_menu():
    code = """
    struct ContextMenuExample: View {
        var body: some View {
            Text("Long press me")
                .contextMenu {
                    Button("Copy") { }
                    Button("Delete", role: .destructive) { }
                }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "ContextMenuExample"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 1
    text = struct.properties[0].value
    assert text.type == "Text"
    assert len(text.modifiers) == 1
    assert text.modifiers[0].name == "contextMenu"

def test_swiftui_swipe_actions():
    code = r"""
    struct SwipeActionsExample: View {
        @State private var items: [String] = []
        
        var body: some View {
            List {
                ForEach(items, id: \.self) { item in
                    Text(item)
                        .swipeActions(edge: .trailing) {
                            Button(role: .destructive) {
                                deleteItem(item)
                            } label: {
                                Label("Delete", systemImage: "trash")
                            }
                        }
                }
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "SwipeActionsExample"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 2
    assert struct.properties[0].name == "items"
    assert struct.properties[0].property_wrapper == "@State"
    list_view = struct.properties[1].value
    assert list_view.type == "List"
    assert len(list_view.children) == 1
    for_each = list_view.children[0]
    assert for_each.type == "ForEach"
    text = for_each.content
    assert text.type == "Text"
    assert len(text.modifiers) == 1
    assert text.modifiers[0].name == "swipeActions"

def test_swiftui_grids():
    code = """
    struct GridExample: View {
        let columns = [
            GridItem(.adaptive(minimum: 100))
        ]
        
        var body: some View {
            ScrollView {
                LazyVGrid(columns: columns, spacing: 20) {
                    ForEach(0..<10) { index in
                        Text("Item \(index)")
                            .frame(height: 100)
                            .background(Color.blue)
                    }
                }
                .padding()
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "GridExample"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 2
    assert struct.properties[0].name == "columns"
    scroll_view = struct.properties[1].value
    assert scroll_view.type == "ScrollView"
    assert len(scroll_view.children) == 1
    grid = scroll_view.children[0]
    assert grid.type == "LazyVGrid"
    assert len(grid.children) == 1
    for_each = grid.children[0]
    assert for_each.type == "ForEach"

def test_swiftui_transitions():
    code = """
    struct TransitionExample: View {
        @State private var isShowing = false
        
        var body: some View {
            VStack {
                if isShowing {
                    Text("Hello")
                        .transition(.scale.combined(with: .opacity))
                }
                
                Button("Toggle") {
                    withAnimation {
                        isShowing.toggle()
                    }
                }
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "TransitionExample"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 2
    assert struct.properties[0].name == "isShowing"
    assert struct.properties[0].property_wrapper == "@State"
    vstack = struct.properties[1].value
    assert vstack.type == "VStack"
    assert len(vstack.children) == 2
    text = vstack.children[0].content
    assert text.type == "Text"
    assert len(text.modifiers) == 1
    assert text.modifiers[0].name == "transition"

def test_swiftui_geometry_reader():
    code = """
    struct GeometryExample: View {
        var body: some View {
            GeometryReader { geometry in
                VStack {
                    Text("Width: \(geometry.size.width)")
                    Text("Height: \(geometry.size.height)")
                }
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "GeometryExample"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 1
    geometry_reader = struct.properties[0].value
    assert geometry_reader.type == "GeometryReader"
    assert len(geometry_reader.children) == 1
    vstack = geometry_reader.children[0]
    assert vstack.type == "VStack"
    assert len(vstack.children) == 2

def test_swiftui_scrollview():
    code = """
    struct ScrollViewExample: View {
        var body: some View {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 20) {
                    ForEach(0..<5) { index in
                        Text("Item \(index)")
                            .frame(width: 100, height: 100)
                            .background(Color.blue)
                    }
                }
                .padding()
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "ScrollViewExample"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 1
    scroll_view = struct.properties[0].value
    assert scroll_view.type == "ScrollView"
    assert len(scroll_view.children) == 1
    hstack = scroll_view.children[0]
    assert hstack.type == "HStack"
    assert len(hstack.children) == 1
    for_each = hstack.children[0]
    assert for_each.type == "ForEach"

def test_swiftui_complex_view_hierarchy():
    code = """
    struct ComplexHierarchyView: View {
        @State private var selectedTab = 0
        @State private var showingSheet = false
        @State private var searchText = ""
        
        var body: some View {
            TabView(selection: $selectedTab) {
                NavigationView {
                    List {
                        ForEach(0..<10) { index in
                            NavigationLink(destination: DetailView(item: index)) {
                                Text("Item \(index)")
                            }
                        }
                    }
                    .searchable(text: $searchText)
                    .navigationTitle("Items")
                    .toolbar {
                        ToolbarItem(placement: .navigationBarTrailing) {
                            Button("Add") {
                                showingSheet = true
                            }
                        }
                    }
                }
                .tabItem {
                    Label("List", systemImage: "list.bullet")
                }
                .tag(0)
                
                SettingsView()
                    .tabItem {
                        Label("Settings", systemImage: "gear")
                    }
                    .tag(1)
            }
            .sheet(isPresented: $showingSheet) {
                AddItemView()
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "ComplexHierarchyView"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 4
    assert all(p.property_wrapper == "@State" for p in struct.properties[:3])
    tab_view = struct.properties[3].value
    assert tab_view.type == "TabView"
    assert len(tab_view.children) == 2
    navigation_view = tab_view.children[0]
    assert navigation_view.type == "NavigationView"
    assert len(navigation_view.children) == 1
    list_view = navigation_view.children[0]
    assert list_view.type == "List"
    assert len(list_view.modifiers) == 3

def test_swiftui_safe_area():
    code = """
    struct SafeAreaExample: View {
        var body: some View {
            Text("Content")
                .safeAreaInset(edge: .bottom) {
                    Color.blue
                        .frame(height: 50)
                }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "SafeAreaExample"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 1
    text = struct.properties[0].value
    assert text.type == "Text"
    assert len(text.modifiers) == 1
    assert text.modifiers[0].name == "safeAreaInset"

def test_swiftui_scene_storage():
    code = """
    struct SceneStorageExample: View {
        @SceneStorage("selectedTab") private var selectedTab = 0
        
        var body: some View {
            TabView(selection: $selectedTab) {
                Text("Tab 1").tag(0)
                Text("Tab 2").tag(1)
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "SceneStorageExample"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 2
    assert struct.properties[0].name == "selectedTab"
    assert struct.properties[0].property_wrapper == "@SceneStorage"
    tab_view = struct.properties[1].value
    assert tab_view.type == "TabView"
    assert len(tab_view.children) == 2

def test_swiftui_app_storage():
    code = """
    struct AppStorageExample: View {
        @AppStorage("username") private var username = ""
        
        var body: some View {
            TextField("Username", text: $username)
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "AppStorageExample"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 2
    assert struct.properties[0].name == "username"
    assert struct.properties[0].property_wrapper == "@AppStorage"
    text_field = struct.properties[1].value
    assert text_field.type == "TextField"
    assert len(text_field.modifiers) == 0

def test_swiftui_charts():
    code = r"""
    struct ChartExample: View {
        let data: [Double]
        
        var body: some View {
            Chart {
                ForEach(data, id: \.self) { value in
                    LineMark(
                        x: .value("Index", data.firstIndex(of: value) ?? 0),
                        y: .value("Value", value)
                    )
                }
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "ChartExample"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 2
    assert struct.properties[0].name == "data"
    chart = struct.properties[1].value
    assert chart.type == "Chart"
    assert len(chart.children) == 1
    for_each = chart.children[0]
    assert for_each.type == "ForEach"

def test_swiftui_maps():
    code = """
    struct MapExample: View {
        @State private var region = MKCoordinateRegion(
            center: CLLocationCoordinate2D(latitude: 37.7749, longitude: -122.4194),
            span: MKCoordinateSpan(latitudeDelta: 0.2, longitudeDelta: 0.2)
        )
        
        var body: some View {
            Map(coordinateRegion: $region)
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "MapExample"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 2
    assert struct.properties[0].name == "region"
    assert struct.properties[0].property_wrapper == "@State"
    map_view = struct.properties[1].value
    assert map_view.type == "Map"
    assert len(map_view.modifiers) == 0

def test_swiftui_date_picker():
    code = """
    struct DatePickerExample: View {
        @State private var date = Date()
        
        var body: some View {
            DatePicker(
                "Select Date",
                selection: $date,
                displayedComponents: [.date, .hourAndMinute]
            )
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "DatePickerExample"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 2
    assert struct.properties[0].name == "date"
    assert struct.properties[0].property_wrapper == "@State"
    date_picker = struct.properties[1].value
    assert date_picker.type == "DatePicker"
    assert len(date_picker.modifiers) == 0

def test_swiftui_color_picker():
    code = """
    struct ColorPickerExample: View {
        @State private var color = Color.blue
        
        var body: some View {
            ColorPicker("Select Color", selection: $color)
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "ColorPickerExample"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 2
    assert struct.properties[0].name == "color"
    assert struct.properties[0].property_wrapper == "@State"
    color_picker = struct.properties[1].value
    assert color_picker.type == "ColorPicker"
    assert len(color_picker.modifiers) == 0

def test_swiftui_progress_view():
    code = """
    struct ProgressViewExample: View {
        @State private var progress = 0.5
        
        var body: some View {
            VStack {
                ProgressView(value: progress)
                ProgressView("Loading...")
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "ProgressViewExample"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 2
    assert struct.properties[0].name == "progress"
    assert struct.properties[0].property_wrapper == "@State"
    vstack = struct.properties[1].value
    assert vstack.type == "VStack"
    assert len(vstack.children) == 2
    assert all(child.type == "ProgressView" for child in vstack.children)

def test_swiftui_gauge():
    code = """
    struct GaugeExample: View {
        @State private var value = 0.7
        
        var body: some View {
            Gauge(value: value, in: 0...1) {
                Text("Progress")
            } currentValueLabel: {
                Text("\(Int(value * 100))%")
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "GaugeExample"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 2
    assert struct.properties[0].name == "value"
    assert struct.properties[0].property_wrapper == "@State"
    gauge = struct.properties[1].value
    assert gauge.type == "Gauge"
    assert len(gauge.modifiers) == 0

def test_swiftui_button_styles():
    code = """
    struct ButtonStylesExample: View {
        var body: some View {
            VStack {
                Button("Plain") { }
                    .buttonStyle(.plain)
                
                Button("Bordered") { }
                    .buttonStyle(.bordered)
                
                Button("Bordered Prominent") { }
                    .buttonStyle(.borderedProminent)
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "ButtonStylesExample"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 1
    vstack = struct.properties[0].value
    assert vstack.type == "VStack"
    assert len(vstack.children) == 3
    assert all(child.type == "Button" for child in vstack.children)
    assert all(len(child.modifiers) == 1 for child in vstack.children)
    assert all(child.modifiers[0].name == "buttonStyle" for child in vstack.children)

def test_swiftui_text_styles():
    code = """
    struct TextStylesExample: View {
        var body: some View {
            VStack {
                Text("Title")
                    .font(.title)
                
                Text("Headline")
                    .font(.headline)
                
                Text("Body")
                    .font(.body)
                
                Text("Caption")
                    .font(.caption)
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "TextStylesExample"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 1
    vstack = struct.properties[0].value
    assert vstack.type == "VStack"
    assert len(vstack.children) == 4
    assert all(child.type == "Text" for child in vstack.children)
    assert all(len(child.modifiers) == 1 for child in vstack.children)
    assert all(child.modifiers[0].name == "font" for child in vstack.children)

def test_swiftui_closures():
    code = """
    struct ClosuresExample: View {
        @State private var count = 0
        @State private var message = ""
        
        let increment = { count += 1 }
        let updateMessage = { message = "Count: \(count)" }
        
        func fetchData() async {
            // Implementation
        }
        
        var body: some View {
            VStack {
                Button("Increment", action: increment)
                Button("Update Message", action: updateMessage)
                Button("Fetch Data") {
                    Task {
                        await fetchData()
                    }
                }
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "ClosuresExample"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 4
    assert struct.properties[0].name == "count"
    assert struct.properties[0].property_wrapper == "@State"
    assert struct.properties[1].name == "message"
    assert struct.properties[1].property_wrapper == "@State"
    assert struct.properties[2].name == "increment"
    assert struct.properties[3].name == "updateMessage"
    vstack = struct.properties[4].value
    assert vstack.type == "VStack"
    assert len(vstack.children) == 3
    assert all(child.type == "Button" for child in vstack.children) 