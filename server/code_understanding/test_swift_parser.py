import pytest
from .language_adapters import SwiftParserAdapter

@pytest.fixture
def swift_parser():
    """Create a Swift parser adapter instance."""
    return SwiftParserAdapter()

def test_empty_input(swift_parser):
    """Test handling of empty input."""
    with pytest.raises(ValueError):
        swift_parser.parse("")

def test_import_declaration(swift_parser):
    """Test parsing of import declarations."""
    code = """
    import SwiftUI
    import Foundation
    """
    result = swift_parser.parse(code)
    assert len(result.imports) == 2
    assert any(imp['module'] == 'SwiftUI' for imp in result.imports)
    assert any(imp['module'] == 'Foundation' for imp in result.imports)

def test_function_declaration(swift_parser):
    """Test parsing of function declarations."""
    code = """
    func calculateSum(a: Int, b: Int) -> Int {
        return a + b
    }
    
    func fetchData() async throws -> Data {
        // Implementation
    }
    """
    result = swift_parser.parse(code)
    assert len(result.functions) == 2
    assert any(f['name'] == 'calculateSum' for f in result.functions)
    assert any(f['name'] == 'fetchData' and f['is_async'] for f in result.functions)

def test_class_declaration(swift_parser):
    """Test parsing of class declarations."""
    code = """
    class User {
        var name: String
        var age: Int
        
        init(name: String, age: Int) {
            self.name = name
            self.age = age
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.classes) == 1
    user_class = result.classes[0]
    assert user_class['name'] == 'User'
    assert len(user_class['methods']) == 1  # init method
    assert len(result.variables) == 2  # name and age properties

def test_struct_declaration(swift_parser):
    """Test parsing of struct declarations."""
    code = """
    struct Point {
        var x: Double
        var y: Double
        
        func distance() -> Double {
            return sqrt(x * x + y * y)
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.classes) == 1
    point_struct = result.classes[0]
    assert point_struct['name'] == 'Point'
    assert point_struct['type'] == 'struct'
    assert len(point_struct['methods']) == 1

def test_protocol_declaration(swift_parser):
    """Test parsing of protocol declarations."""
    code = """
    protocol Identifiable {
        var id: String { get }
        func validate() -> Bool
    }
    """
    result = swift_parser.parse(code)
    assert len(result.protocols) == 1
    protocol = result.protocols[0]
    assert protocol['name'] == 'Identifiable'
    assert len(protocol['requirements']) == 2

def test_extension_declaration(swift_parser):
    """Test parsing of extension declarations."""
    code = """
    extension String {
        func isPalindrome() -> Bool {
            return self == String(self.reversed())
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.extensions) == 1
    extension = result.extensions[0]
    assert extension['type'] == 'String'
    assert len(extension['methods']) == 1

def test_swiftui_view(swift_parser):
    """Test parsing of SwiftUI views."""
    code = """
    struct ContentView: View {
        @State private var text = ""
        @Binding var isPresented: Bool
        
        var body: some View {
            Text(text)
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ContentView'
    assert len(view['properties']) == 2  # text and isPresented

def test_property_wrapper(swift_parser):
    """Test parsing of property wrappers."""
    code = """
    class ViewModel: ObservableObject {
        @Published var count = 0
        @AppStorage("username") var username: String = ""
    }
    """
    result = swift_parser.parse(code)
    assert len(result.variables) == 2
    assert any(v['has_wrapper'] and v['name'] == 'count' for v in result.variables)
    assert any(v['has_wrapper'] and v['name'] == 'username' for v in result.variables)

def test_error_handling(swift_parser):
    """Test error handling for malformed code."""
    code = """
    class InvalidClass {
        func invalidFunction( {
            // Missing closing parenthesis
        }
    }
    """
    with pytest.raises(ValueError):
        swift_parser.parse(code)

def test_complex_swiftui_view(swift_parser):
    """Test parsing of a complex SwiftUI view with nested views."""
    code = """
    struct MainView: View {
        @StateObject private var viewModel = ViewModel()
        @Environment(\.colorScheme) var colorScheme
        
        var body: some View {
            NavigationView {
                List {
                    ForEach(viewModel.items) { item in
                        ItemRow(item: item)
                    }
                }
                .navigationTitle("Items")
                .toolbar {
                    ToolbarItem(placement: .navigationBarTrailing) {
                        Button("Add") {
                            viewModel.addItem()
                        }
                    }
                }
            }
        }
    }
    
    struct ItemRow: View {
        let item: Item
        
        var body: some View {
            HStack {
                Text(item.name)
                Spacer()
                Text(item.description)
                    .foregroundColor(.secondary)
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 2
    assert any(v['name'] == 'MainView' for v in result.views)
    assert any(v['name'] == 'ItemRow' for v in result.views)
    assert len(result.variables) >= 2  # viewModel and colorScheme

def test_async_await(swift_parser):
    """Test parsing of async/await code."""
    code = """
    class DataService {
        func fetchData() async throws -> [Item] {
            let url = URL(string: "https://api.example.com/items")!
            let (data, _) = try await URLSession.shared.data(from: url)
            return try JSONDecoder().decode([Item].self, from: data)
        }
        
        func processItems() async {
            do {
                let items = try await fetchData()
                for item in items {
                    await processItem(item)
                }
            } catch {
                print("Error: \(error)")
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.functions) == 2
    assert all(f['is_async'] for f in result.functions)

def test_protocol_extension(swift_parser):
    """Test parsing of protocol extensions."""
    code = """
    protocol Identifiable {
        var id: String { get }
    }
    
    extension Identifiable {
        func validate() -> Bool {
            return !id.isEmpty
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.protocols) == 1
    assert len(result.extensions) == 1
    assert result.extensions[0]['type'] == 'Identifiable'

def test_generic_types(swift_parser):
    """Test parsing of generic types."""
    code = """
    struct Stack<Element> {
        private var items: [Element] = []
        
        mutating func push(_ item: Element) {
            items.append(item)
        }
        
        mutating func pop() -> Element? {
            return items.popLast()
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.classes) == 1
    stack = result.classes[0]
    assert stack['name'] == 'Stack'
    assert len(stack['methods']) == 2

def test_property_observers(swift_parser):
    """Test parsing of property observers."""
    code = """
    class User {
        var name: String {
            willSet {
                print("Will set name to \(newValue)")
            }
            didSet {
                print("Did set name from \(oldValue) to \(name)")
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.variables) == 1
    assert result.variables[0]['name'] == 'name'

def test_swiftui_modifiers(swift_parser):
    """Test parsing of SwiftUI view modifiers."""
    code = """
    struct ModifiedView: View {
        var body: some View {
            Text("Hello")
                .font(.title)
                .foregroundColor(.blue)
                .padding()
                .background(Color.gray)
                .cornerRadius(10)
                .shadow(radius: 5)
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ModifiedView'
    assert len(view['modifiers']) >= 6  # All the modifiers applied

def test_swiftui_environment_values(swift_parser):
    """Test parsing of SwiftUI environment values."""
    code = """
    struct EnvironmentView: View {
        @Environment(\.colorScheme) var colorScheme
        @Environment(\.locale) var locale
        @Environment(\.calendar) var calendar
        @Environment(\.timeZone) var timeZone
        
        var body: some View {
            Text("Environment Test")
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert len(view['environment_values']) == 4
    assert all(v['has_wrapper'] and v['wrapper_type'] == 'Environment' for v in view['environment_values'])

def test_swiftui_preview(swift_parser):
    """Test parsing of SwiftUI preview providers."""
    code = """
    struct ContentView_Previews: PreviewProvider {
        static var previews: some View {
            ContentView()
                .previewDevice(PreviewDevice(rawValue: "iPhone 12"))
                .previewDisplayName("iPhone 12")
            
            ContentView()
                .preferredColorScheme(.dark)
                .previewDisplayName("Dark Mode")
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.preview_providers) == 1
    preview = result.preview_providers[0]
    assert preview['name'] == 'ContentView_Previews'
    assert len(preview['previews']) == 2

def test_swiftui_gestures(swift_parser):
    """Test parsing of SwiftUI gesture modifiers."""
    code = """
    struct GestureView: View {
        @State private var offset = CGSize.zero
        
        var body: some View {
            Image(systemName: "star")
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
                .offset(offset)
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert len(view['gestures']) == 1
    assert view['gestures'][0]['type'] == 'DragGesture'

def test_swiftui_animations(swift_parser):
    """Test parsing of SwiftUI animations."""
    code = """
    struct AnimatedView: View {
        @State private var isAnimating = false
        
        var body: some View {
            Circle()
                .fill(isAnimating ? Color.blue : Color.red)
                .frame(width: 100, height: 100)
                .scaleEffect(isAnimating ? 1.2 : 1.0)
                .animation(.spring(response: 0.5, dampingFraction: 0.6), value: isAnimating)
                .onTapGesture {
                    withAnimation {
                        isAnimating.toggle()
                    }
                }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert len(view['animations']) == 1
    assert view['animations'][0]['type'] == 'spring'

def test_swiftui_sheets(swift_parser):
    """Test parsing of SwiftUI sheet presentations."""
    code = """
    struct SheetView: View {
        @State private var showingSheet = false
        
        var body: some View {
            Button("Show Sheet") {
                showingSheet = true
            }
            .sheet(isPresented: $showingSheet) {
                NavigationView {
                    Text("Sheet Content")
                        .navigationTitle("Sheet")
                        .navigationBarItems(trailing: Button("Done") {
                            showingSheet = false
                        })
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert len(view['sheets']) == 1
    assert view['sheets'][0]['is_presented'] == 'showingSheet'

def test_swiftui_navigation(swift_parser):
    """Test parsing of SwiftUI navigation."""
    code = """
    struct NavigationView: View {
        var body: some View {
            NavigationView {
                List {
                    NavigationLink(destination: DetailView()) {
                        Text("Go to Detail")
                    }
                }
                .navigationTitle("Main View")
                .navigationBarItems(trailing: Button("Add") {
                    // Add action
                })
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert len(view['navigation_links']) == 1
    assert view['navigation_title'] == "Main View"

def test_swiftui_tabview(swift_parser):
    """Test parsing of SwiftUI tab views."""
    code = """
    struct TabView: View {
        var body: some View {
            TabView {
                HomeView()
                    .tabItem {
                        Label("Home", systemImage: "house")
                    }
                
                ProfileView()
                    .tabItem {
                        Label("Profile", systemImage: "person")
                    }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert len(view['tab_items']) == 2
    assert all(tab['has_label'] for tab in view['tab_items'])

def test_swiftui_alerts(swift_parser):
    """Test parsing of SwiftUI alerts."""
    code = """
    struct AlertView: View {
        @State private var showingAlert = false
        
        var body: some View {
            Button("Show Alert") {
                showingAlert = true
            }
            .alert("Important", isPresented: $showingAlert) {
                Button("OK", role: .cancel) { }
                Button("Delete", role: .destructive) {
                    // Delete action
                }
            } message: {
                Text("This action cannot be undone.")
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert len(view['alerts']) == 1
    alert = view['alerts'][0]
    assert alert['title'] == "Important"
    assert len(alert['buttons']) == 2

def test_swiftui_forms(swift_parser):
    """Test parsing of SwiftUI forms."""
    code = """
    struct FormView: View {
        @State private var username = ""
        @State private var isSubscribed = false
        
        var body: some View {
            Form {
                Section(header: Text("Account")) {
                    TextField("Username", text: $username)
                    Toggle("Subscribe", isOn: $isSubscribed)
                }
                
                Section(header: Text("Actions")) {
                    Button("Save") {
                        // Save action
                    }
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert len(view['form_sections']) == 2
    assert len(view['form_controls']) == 3  # TextField, Toggle, and Button

def test_swiftui_lists(swift_parser):
    """Test parsing of SwiftUI lists with different data sources."""
    code = """
    struct ListView: View {
        let items = ["Item 1", "Item 2", "Item 3"]
        
        var body: some View {
            List {
                ForEach(items, id: \\.self) { item in
                    Text(item)
                }
                
                Section(header: Text("Static Items")) {
                    Text("Static Item 1")
                    Text("Static Item 2")
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert len(view['list_items']) >= 5  # 3 dynamic + 2 static items
    assert len(view['list_sections']) == 1

def test_swiftui_grids(swift_parser):
    """Test parsing of SwiftUI grids."""
    code = """
    struct GridView: View {
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
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert len(view['grid_items']) == 10
    assert view['grid_type'] == 'LazyVGrid'

def test_swiftui_transitions(swift_parser):
    """Test parsing of SwiftUI transitions."""
    code = """
    struct TransitionView: View {
        @State private var isShowing = false
        
        var body: some View {
            VStack {
                if isShowing {
                    Text("Hello")
                        .transition(.scale.combined(with: .opacity))
                }
                
                Button("Toggle") {
                    withAnimation(.spring()) {
                        isShowing.toggle()
                    }
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert len(view['transitions']) == 1
    assert view['transitions'][0]['type'] == 'combined'

def test_swiftui_geometry_reader(swift_parser):
    """Test parsing of SwiftUI geometry reader."""
    code = """
    struct GeometryView: View {
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
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert len(view['geometry_readers']) == 1
    assert view['geometry_readers'][0]['has_proxy']

def test_swiftui_scrollview(swift_parser):
    """Test parsing of SwiftUI scroll views."""
    code = """
    struct ScrollView: View {
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
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert len(view['scroll_views']) == 1
    assert view['scroll_views'][0]['axis'] == 'horizontal'

def test_swiftui_async_image(swift_parser):
    """Test parsing of SwiftUI async image."""
    code = """
    struct AsyncImageView: View {
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
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert len(view['async_images']) == 1
    assert view['async_images'][0]['has_phase_handling']

def test_swiftui_custom_modifiers(swift_parser):
    """Test parsing of SwiftUI custom modifiers."""
    code = """
    struct CardStyle: ViewModifier {
        func body(content: Content) -> some View {
            content
                .padding()
                .background(Color.white)
                .cornerRadius(10)
                .shadow(radius: 5)
        }
    }
    
    struct CustomModifierView: View {
        var body: some View {
            Text("Hello")
                .modifier(CardStyle())
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.view_modifiers) == 1
    assert len(result.views) == 1
    assert result.view_modifiers[0]['name'] == 'CardStyle'
    assert result.views[0]['has_custom_modifier']

def test_swiftui_environment_object(swift_parser):
    """Test parsing of SwiftUI environment objects."""
    code = """
    class UserSettings: ObservableObject {
        @Published var isDarkMode = false
    }
    
    struct EnvironmentObjectView: View {
        @EnvironmentObject var settings: UserSettings
        
        var body: some View {
            Toggle("Dark Mode", isOn: $settings.isDarkMode)
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert len(view['environment_objects']) == 1
    assert view['environment_objects'][0]['type'] == 'UserSettings'

def test_swiftui_custom_bindings(swift_parser):
    """Test parsing of SwiftUI custom bindings."""
    code = """
    struct CustomBindingView: View {
        @State private var text = ""
        
        var body: some View {
            TextField("Enter text", text: Binding(
                get: { text },
                set: { newValue in
                    text = newValue.uppercased()
                }
            ))
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert len(view['custom_bindings']) == 1
    assert view['custom_bindings'][0]['has_getter']
    assert view['custom_bindings'][0]['has_setter']

def test_swiftui_preference_key(swift_parser):
    """Test parsing of SwiftUI preference keys."""
    code = """
    struct WidthPreferenceKey: PreferenceKey {
        static var defaultValue: CGFloat = 0
        
        static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) {
            value = max(value, nextValue())
        }
    }
    
    struct PreferenceKeyView: View {
        var body: some View {
            Text("Hello")
                .background(GeometryReader { geometry in
                    Color.clear.preference(
                        key: WidthPreferenceKey.self,
                        value: geometry.size.width
                    )
                })
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.preference_keys) == 1
    assert len(result.views) == 1
    assert result.preference_keys[0]['name'] == 'WidthPreferenceKey'
    assert result.views[0]['has_preference_key']

def test_swiftui_custom_transition(swift_parser):
    """Test parsing of SwiftUI custom transitions."""
    code = """
    struct SlideTransition: AnyTransition {
        static var slide: AnyTransition {
            AnyTransition.asymmetric(
                insertion: .move(edge: .trailing).combined(with: .opacity),
                removal: .move(edge: .leading).combined(with: .opacity)
            )
        }
    }
    
    struct CustomTransitionView: View {
        @State private var isShowing = false
        
        var body: some View {
            if isShowing {
                Text("Hello")
                    .transition(SlideTransition.slide)
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.custom_transitions) == 1
    assert len(result.views) == 1
    assert result.custom_transitions[0]['name'] == 'SlideTransition'
    assert result.views[0]['has_custom_transition']

def test_swiftui_custom_gesture(swift_parser):
    """Test parsing of SwiftUI custom gestures."""
    code = """
    struct LongPressGesture: Gesture {
        let minimumDuration: Double
        let maximumDistance: CGFloat
        
        var body: some Gesture {
            DragGesture(minimumDistance: maximumDistance)
                .onEnded { _ in }
                .simultaneously(with: TapGesture())
        }
    }
    
    struct CustomGestureView: View {
        var body: some View {
            Text("Hello")
                .gesture(LongPressGesture(minimumDuration: 1, maximumDistance: 50))
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.custom_gestures) == 1
    assert len(result.views) == 1
    assert result.custom_gestures[0]['name'] == 'LongPressGesture'
    assert result.views[0]['has_custom_gesture']

def test_swiftui_custom_animation(swift_parser):
    """Test parsing of SwiftUI custom animations."""
    code = """
    struct BounceAnimation: Animation {
        let response: Double
        let dampingFraction: Double
        
        func animate(duration: Double, curve: AnimationCurve) -> Animation {
            .spring(response: response, dampingFraction: dampingFraction)
        }
    }
    
    struct CustomAnimationView: View {
        @State private var isAnimating = false
        
        var body: some View {
            Text("Hello")
                .scaleEffect(isAnimating ? 1.2 : 1.0)
                .animation(BounceAnimation(response: 0.5, dampingFraction: 0.6), value: isAnimating)
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.custom_animations) == 1
    assert len(result.views) == 1
    assert result.custom_animations[0]['name'] == 'BounceAnimation'
    assert result.views[0]['has_custom_animation']

def test_swiftui_custom_transition_animation(swift_parser):
    """Test parsing of SwiftUI custom transition animations."""
    code = """
    struct SlideAndFadeTransition: AnyTransition {
        static var slideAndFade: AnyTransition {
            AnyTransition.modifier(
                active: SlideAndFadeModifier(offset: 50, opacity: 0),
                identity: SlideAndFadeModifier(offset: 0, opacity: 1)
            )
        }
    }
    
    struct SlideAndFadeModifier: ViewModifier {
        let offset: CGFloat
        let opacity: Double
        
        func body(content: Content) -> some View {
            content
                .offset(x: offset)
                .opacity(opacity)
        }
    }
    
    struct CustomTransitionAnimationView: View {
        @State private var isShowing = false
        
        var body: some View {
            if isShowing {
                Text("Hello")
                    .transition(SlideAndFadeTransition.slideAndFade)
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.custom_transitions) == 1
    assert len(result.view_modifiers) == 1
    assert len(result.views) == 1
    assert result.custom_transitions[0]['name'] == 'SlideAndFadeTransition'
    assert result.view_modifiers[0]['name'] == 'SlideAndFadeModifier'
    assert result.views[0]['has_custom_transition']

def test_swiftui_custom_gesture_sequence(swift_parser):
    """Test parsing of SwiftUI custom gesture sequences."""
    code = """
    struct CustomGestureSequenceView: View {
        @State private var offset = CGSize.zero
        
        var body: some View {
            Image(systemName: "star")
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
                        .simultaneously(with: TapGesture().onEnded {
                            print("Tapped")
                        })
                )
                .offset(offset)
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert len(view['gestures']) == 1
    assert view['gestures'][0]['has_sequence']
    assert view['gestures'][0]['sequence_type'] == 'simultaneously'

def test_swiftui_custom_animation_sequence(swift_parser):
    """Test parsing of SwiftUI custom animation sequences."""
    code = """
    struct CustomAnimationSequenceView: View {
        @State private var isAnimating = false
        
        var body: some View {
            Text("Hello")
                .scaleEffect(isAnimating ? 1.2 : 1.0)
                .rotationEffect(.degrees(isAnimating ? 360 : 0))
                .animation(
                    .spring(response: 0.5, dampingFraction: 0.6)
                    .delay(0.2)
                    .repeatCount(2, autoreverses: true),
                    value: isAnimating
                )
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert len(view['animations']) == 1
    assert view['animations'][0]['has_sequence']
    assert view['animations'][0]['sequence_type'] == 'spring'
    assert view['animations'][0]['has_delay']
    assert view['animations'][0]['has_repeat']

def test_swiftui_custom_transition_sequence(swift_parser):
    """Test parsing of SwiftUI custom transition sequences."""
    code = """
    struct CustomTransitionSequenceView: View {
        @State private var isShowing = false
        
        var body: some View {
            if isShowing {
                Text("Hello")
                    .transition(
                        .scale
                        .combined(with: .opacity)
                        .animation(.spring())
                    )
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert len(view['transitions']) == 1
    assert view['transitions'][0]['has_sequence']
    assert view['transitions'][0]['sequence_type'] == 'combined'
    assert view['transitions'][0]['has_animation']

def test_swiftui_custom_gesture_sequence_animation(swift_parser):
    """Test parsing of SwiftUI custom gesture sequence animations."""
    code = """
    struct CustomGestureSequenceAnimationView: View {
        @State private var offset = CGSize.zero
        @State private var scale: CGFloat = 1.0
        
        var body: some View {
            Image(systemName: "star")
                .gesture(
                    DragGesture()
                        .onChanged { gesture in
                            withAnimation(.spring()) {
                                offset = gesture.translation
                            }
                        }
                        .onEnded { _ in
                            withAnimation(.spring(response: 0.5, dampingFraction: 0.6)) {
                                offset = .zero
                            }
                        }
                        .simultaneously(with: TapGesture()
                            .onEnded {
                                withAnimation(.spring()) {
                                    scale = scale == 1.0 ? 1.2 : 1.0
                                }
                            }
                        )
                )
                .offset(offset)
                .scaleEffect(scale)
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert len(view['gestures']) == 1
    assert view['gestures'][0]['has_sequence']
    assert view['gestures'][0]['has_animation']
    assert view['gestures'][0]['sequence_type'] == 'simultaneously'

def test_swiftui_custom_animation_sequence_curve(swift_parser):
    """Test parsing of SwiftUI custom animation sequence curves."""
    code = """
    struct CustomAnimationSequenceCurveView: View {
        @State private var isAnimating = false
        
        var body: some View {
            Text("Hello")
                .scaleEffect(isAnimating ? 1.2 : 1.0)
                .animation(
                    .spring(response: 0.5, dampingFraction: 0.6)
                    .speed(1.2)
                    .repeatCount(2, autoreverses: true),
                    value: isAnimating
                )
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert len(view['animations']) == 1
    assert view['animations'][0]['has_sequence']
    assert view['animations'][0]['has_curve']
    assert view['animations'][0]['sequence_type'] == 'spring'
    assert view['animations'][0]['has_speed']

def test_swiftui_custom_transition_sequence_curve(swift_parser):
    """Test parsing of SwiftUI custom transition sequence curves."""
    code = """
    struct CustomTransitionSequenceCurveView: View {
        @State private var isShowing = false
        
        var body: some View {
            if isShowing {
                Text("Hello")
                    .transition(
                        .scale
                        .combined(with: .opacity)
                        .animation(.spring(response: 0.5, dampingFraction: 0.6))
                    )
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert len(view['transitions']) == 1
    assert view['transitions'][0]['has_sequence']
    assert view['transitions'][0]['has_curve']
    assert view['transitions'][0]['sequence_type'] == 'combined'
    assert view['transitions'][0]['curve_type'] == 'spring'

def test_swiftui_custom_gesture_sequence_animation_curve(swift_parser):
    """Test parsing of SwiftUI custom gesture sequence animation curves."""
    code = """
    struct CustomGestureSequenceAnimationCurveView: View {
        @State private var offset = CGSize.zero
        @State private var scale: CGFloat = 1.0
        
        var body: some View {
            Image(systemName: "star")
                .gesture(
                    DragGesture()
                        .onChanged { gesture in
                            withAnimation(.spring(response: 0.5, dampingFraction: 0.6)) {
                                offset = gesture.translation
                            }
                        }
                        .onEnded { _ in
                            withAnimation(.spring(response: 0.5, dampingFraction: 0.6)) {
                                offset = .zero
                            }
                        }
                        .simultaneously(with: TapGesture()
                            .onEnded {
                                withAnimation(.spring(response: 0.5, dampingFraction: 0.6)) {
                                    scale = scale == 1.0 ? 1.2 : 1.0
                                }
                            }
                        )
                )
                .offset(offset)
                .scaleEffect(scale)
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert len(view['gestures']) == 1
    assert view['gestures'][0]['has_sequence']
    assert view['gestures'][0]['has_animation']
    assert view['gestures'][0]['has_curve']
    assert view['gestures'][0]['sequence_type'] == 'simultaneously'
    assert view['gestures'][0]['curve_type'] == 'spring'

def test_swiftui_custom_animation_sequence_curve_priority(swift_parser):
    """Test parsing of SwiftUI custom animation sequence curve priorities."""
    code = """
    struct CustomAnimationSequenceCurvePriorityView: View {
        @State private var isAnimating = false
        
        var body: some View {
            Text("Hello")
                .scaleEffect(isAnimating ? 1.2 : 1.0)
                .animation(
                    .spring(response: 0.5, dampingFraction: 0.6)
                    .speed(1.2)
                    .repeatCount(2, autoreverses: true)
                    .priority(.high),
                    value: isAnimating
                )
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert len(view['animations']) == 1
    assert view['animations'][0]['has_sequence']
    assert view['animations'][0]['has_curve']
    assert view['animations'][0]['has_priority']
    assert view['animations'][0]['sequence_type'] == 'spring'
    assert view['animations'][0]['priority'] == 'high'

def test_swiftui_charts(swift_parser):
    """Test parsing of SwiftUI charts."""
    code = """
    struct ChartView: View {
        let data = [1.0, 2.0, 3.0, 4.0, 5.0]
        
        var body: some View {
            Chart {
                ForEach(data, id: \\.self) { value in
                    LineMark(
                        x: .value("Index", data.firstIndex(of: value)!),
                        y: .value("Value", value)
                    )
                    .foregroundStyle(.blue)
                }
            }
            .chartXAxis {
                AxisMarks(values: .automatic)
            }
            .chartYAxis {
                AxisMarks(values: .automatic)
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ChartView'
    assert len(view['charts']) == 1
    assert view['charts'][0]['has_marks']
    assert view['charts'][0]['has_axes']

def test_swiftui_canvas(swift_parser):
    """Test parsing of SwiftUI canvas."""
    code = """
    struct CanvasView: View {
        var body: some View {
            Canvas { context, size in
                context.fill(
                    Path(ellipseIn: CGRect(x: 0, y: 0, width: size.width, height: size.height)),
                    with: .color(.blue)
                )
            }
            .frame(width: 200, height: 200)
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'CanvasView'
    assert len(view['canvases']) == 1
    assert view['canvases'][0]['has_context']
    assert view['canvases'][0]['has_size']

def test_swiftui_timeline_view(swift_parser):
    """Test parsing of SwiftUI timeline view."""
    code = """
    struct TimelineView: View {
        var body: some View {
            TimelineView(.animation) { timeline in
                Text("Current time: \(timeline.date)")
                    .font(.title)
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'TimelineView'
    assert len(view['timeline_views']) == 1
    assert view['timeline_views'][0]['has_schedule']
    assert view['timeline_views'][0]['has_context']

def test_swiftui_share_link(swift_parser):
    """Test parsing of SwiftUI share link."""
    code = """
    struct ShareLinkView: View {
        let text = "Check out this amazing app!"
        let url = URL(string: "https://example.com")!
        
        var body: some View {
            ShareLink(
                item: text,
                subject: Text("App Recommendation"),
                message: Text("I thought you might like this app"),
                preview: SharePreview(
                    "App Name",
                    image: Image(systemName: "star")
                )
            )
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ShareLinkView'
    assert len(view['share_links']) == 1
    assert view['share_links'][0]['has_preview']
    assert view['share_links'][0]['has_subject']

def test_swiftui_photos_picker(swift_parser):
    """Test parsing of SwiftUI photos picker."""
    code = """
    struct PhotosPickerView: View {
        @State private var selectedItem: PhotosPickerItem?
        @State private var selectedImage: Image?
        
        var body: some View {
            PhotosPicker(
                selection: $selectedItem,
                matching: .images,
                photoLibrary: .shared()
            ) {
                Label("Select Image", systemImage: "photo")
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'PhotosPickerView'
    assert len(view['photos_pickers']) == 1
    assert view['photos_pickers'][0]['has_selection']
    assert view['photos_pickers'][0]['has_matching']

def test_swiftui_camera(swift_parser):
    """Test parsing of SwiftUI camera."""
    code = """
    struct CameraView: View {
        @StateObject private var camera = CameraModel()
        
        var body: some View {
            ZStack {
                CameraPreview(camera: camera)
                    .ignoresSafeArea()
                
                VStack {
                    Spacer()
                    Button("Take Photo") {
                        camera.takePicture()
                    }
                    .padding()
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'CameraView'
    assert len(view['cameras']) == 1
    assert view['cameras'][0]['has_preview']
    assert view['cameras'][0]['has_controls']

def test_swiftui_location_button(swift_parser):
    """Test parsing of SwiftUI location button."""
    code = """
    struct LocationButtonView: View {
        @StateObject private var locationManager = LocationManager()
        
        var body: some View {
            LocationButton {
                locationManager.requestLocation()
            } label: {
                Label("Share Location", systemImage: "location")
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'LocationButtonView'
    assert len(view['location_buttons']) == 1
    assert view['location_buttons'][0]['has_action']
    assert view['location_buttons'][0]['has_label']

def test_swiftui_activity_indicator(swift_parser):
    """Test parsing of SwiftUI activity indicator."""
    code = """
    struct ActivityIndicatorView: View {
        @State private var isLoading = true
        
        var body: some View {
            if isLoading {
                ProgressView()
                    .progressViewStyle(CircularProgressViewStyle())
                    .scaleEffect(1.5)
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ActivityIndicatorView'
    assert len(view['progress_views']) == 1
    assert view['progress_views'][0]['has_style']
    assert view['progress_views'][0]['has_scale']

def test_swiftui_refreshable(swift_parser):
    """Test parsing of SwiftUI refreshable modifier."""
    code = """
    struct RefreshableView: View {
        @State private var items: [String] = []
        
        var body: some View {
            List(items, id: \\.self) { item in
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
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'RefreshableView'
    assert len(view['refreshable_views']) == 1
    assert view['refreshable_views'][0]['has_action']
    assert view['refreshable_views'][0]['action_is_async']

def test_swiftui_searchable(swift_parser):
    """Test parsing of SwiftUI searchable modifier."""
    code = """
    struct SearchableView: View {
        @State private var searchText = ""
        @State private var items: [String] = []
        
        var body: some View {
            List(filteredItems, id: \\.self) { item in
                Text(item)
            }
            .searchable(text: $searchText, prompt: "Search items")
        }
        
        var filteredItems: [String] {
            if searchText.isEmpty {
                return items
            }
            return items.filter { $0.localizedCaseInsensitiveContains(searchText) }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'SearchableView'
    assert len(view['searchable_views']) == 1
    assert view['searchable_views'][0]['has_text']
    assert view['searchable_views'][0]['has_prompt']

def test_swiftui_toolbar_placement(swift_parser):
    """Test parsing of SwiftUI toolbar placement."""
    code = """
    struct ToolbarPlacementView: View {
        var body: some View {
            NavigationView {
                Text("Content")
                    .toolbar {
                        ToolbarItem(placement: .navigationBarLeading) {
                            Button("Leading") { }
                        }
                        ToolbarItem(placement: .navigationBarTrailing) {
                            Button("Trailing") { }
                        }
                        ToolbarItem(placement: .bottomBar) {
                            Button("Bottom") { }
                        }
                    }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ToolbarPlacementView'
    assert len(view['toolbar_items']) == 3
    assert any(item['placement'] == 'navigationBarLeading' for item in view['toolbar_items'])
    assert any(item['placement'] == 'navigationBarTrailing' for item in view['toolbar_items'])
    assert any(item['placement'] == 'bottomBar' for item in view['toolbar_items'])

def test_swiftui_safe_area(swift_parser):
    """Test parsing of SwiftUI safe area handling."""
    code = """
    struct SafeAreaView: View {
        var body: some View {
            ZStack {
                Color.blue
                    .ignoresSafeArea()
                
                VStack {
                    Text("Content")
                        .padding()
                }
                .safeAreaInset(edge: .bottom) {
                    Color.red
                        .frame(height: 50)
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'SafeAreaView'
    assert len(view['safe_area_insets']) == 1
    assert view['safe_area_insets'][0]['edge'] == 'bottom'
    assert any(node['ignores_safe_area'] for node in view['nodes'])

def test_swiftui_scene_storage(swift_parser):
    """Test parsing of SwiftUI scene storage."""
    code = """
    struct SceneStorageView: View {
        @SceneStorage("selectedTab") private var selectedTab = 0
        
        var body: some View {
            TabView(selection: $selectedTab) {
                Text("Tab 1")
                    .tag(0)
                Text("Tab 2")
                    .tag(1)
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'SceneStorageView'
    assert len(view['scene_storage']) == 1
    assert view['scene_storage'][0]['key'] == 'selectedTab'
    assert view['scene_storage'][0]['has_default_value']

def test_swiftui_app_storage(swift_parser):
    """Test parsing of SwiftUI app storage."""
    code = """
    struct AppStorageView: View {
        @AppStorage("username") private var username = ""
        @AppStorage("isDarkMode") private var isDarkMode = false
        
        var body: some View {
            VStack {
                TextField("Username", text: $username)
                Toggle("Dark Mode", isOn: $isDarkMode)
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'AppStorageView'
    assert len(view['app_storage']) == 2
    assert any(storage['key'] == 'username' for storage in view['app_storage'])
    assert any(storage['key'] == 'isDarkMode' for storage in view['app_storage'])

def test_swiftui_focus_state(swift_parser):
    """Test parsing of SwiftUI focus state."""
    code = """
    struct FocusStateView: View {
        @FocusState private var isFocused: Bool
        
        var body: some View {
            TextField("Enter text", text: .constant(""))
                .focused($isFocused)
                .onChange(of: isFocused) { newValue in
                    print("Focus changed: \(newValue)")
                }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'FocusStateView'
    assert len(view['focus_states']) == 1
    assert view['focus_states'][0]['has_binding']
    assert view['focus_states'][0]['has_on_change']

def test_swiftui_scroll_target(swift_parser):
    """Test parsing of SwiftUI scroll target."""
    code = """
    struct ScrollTargetView: View {
        @State private var scrollPosition: Int?
        
        var body: some View {
            ScrollView {
                LazyVStack {
                    ForEach(0..<10) { index in
                        Text("Item \(index)")
                            .scrollTransition { content, phase in
                                content
                                    .opacity(phase.isIdentity ? 1 : 0)
                            }
                    }
                }
            }
            .scrollTargetBehavior(.viewAligned)
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ScrollTargetView'
    assert len(view['scroll_targets']) == 1
    assert view['scroll_targets'][0]['behavior'] == 'viewAligned'
    assert view['scroll_targets'][0]['has_transition']

def test_swiftui_scroll_indicator(swift_parser):
    """Test parsing of SwiftUI scroll indicator."""
    code = """
    struct ScrollIndicatorView: View {
        var body: some View {
            ScrollView {
                LazyVStack {
                    ForEach(0..<10) { index in
                        Text("Item \(index)")
                    }
                }
            }
            .scrollIndicators(.hidden)
            .scrollIndicatorsFlash(trigger: true)
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ScrollIndicatorView'
    assert len(view['scroll_indicators']) == 1
    assert view['scroll_indicators'][0]['visibility'] == 'hidden'
    assert view['scroll_indicators'][0]['has_flash']

def test_swiftui_scroll_clip_disabled(swift_parser):
    """Test parsing of SwiftUI scroll clip disabled."""
    code = """
    struct ScrollClipDisabledView: View {
        var body: some View {
            ScrollView {
                VStack {
                    ForEach(0..<10) { index in
                        Text("Item \(index)")
                            .frame(height: 100)
                    }
                }
            }
            .scrollClipDisabled()
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ScrollClipDisabledView'
    assert view['scroll_clip_disabled']

def test_swiftui_scroll_position(swift_parser):
    """Test parsing of SwiftUI scroll position."""
    code = """
    struct ScrollPositionView: View {
        @State private var scrollPosition: Int?
        
        var body: some View {
            ScrollView {
                LazyVStack {
                    ForEach(0..<10) { index in
                        Text("Item \(index)")
                    }
                }
            }
            .scrollPosition(id: $scrollPosition)
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ScrollPositionView'
    assert len(view['scroll_positions']) == 1
    assert view['scroll_positions'][0]['has_binding']
    assert view['scroll_positions'][0]['binding_type'] == 'id'

def test_swiftui_scroll_target_behavior(swift_parser):
    """Test parsing of SwiftUI scroll target behavior."""
    code = """
    struct ScrollTargetBehaviorView: View {
        var body: some View {
            ScrollView {
                LazyVStack {
                    ForEach(0..<10) { index in
                        Text("Item \(index)")
                    }
                }
            }
            .scrollTargetBehavior(.viewAligned)
            .scrollTargetLayout()
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ScrollTargetBehaviorView'
    assert len(view['scroll_target_behaviors']) == 1
    assert view['scroll_target_behaviors'][0]['behavior'] == 'viewAligned'
    assert view['scroll_target_behaviors'][0]['has_layout']

def test_swiftui_scroll_transition(swift_parser):
    """Test parsing of SwiftUI scroll transition."""
    code = """
    struct ScrollTransitionView: View {
        var body: some View {
            ScrollView {
                LazyVStack {
                    ForEach(0..<10) { index in
                        Text("Item \(index)")
                            .scrollTransition { content, phase in
                                content
                                    .opacity(phase.isIdentity ? 1 : 0)
                                    .scaleEffect(phase.isIdentity ? 1 : 0.8)
                            }
                    }
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ScrollTransitionView'
    assert len(view['scroll_transitions']) == 1
    assert view['scroll_transitions'][0]['has_phase']
    assert view['scroll_transitions'][0]['has_content']
    assert view['scroll_transitions'][0]['has_effects']

def test_swiftui_scroll_transition_phase(swift_parser):
    """Test parsing of SwiftUI scroll transition phase."""
    code = """
    struct ScrollTransitionPhaseView: View {
        var body: some View {
            ScrollView {
                LazyVStack {
                    ForEach(0..<10) { index in
                        Text("Item \(index)")
                            .scrollTransition { content, phase in
                                content
                                    .opacity(phase.isIdentity ? 1 : 0)
                                    .scaleEffect(phase.isIdentity ? 1 : 0.8)
                                    .rotationEffect(.degrees(phase.isIdentity ? 0 : 45))
                            }
                    }
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ScrollTransitionPhaseView'
    assert len(view['scroll_transitions']) == 1
    assert view['scroll_transitions'][0]['has_phase']
    assert view['scroll_transitions'][0]['has_identity_check']
    assert view['scroll_transitions'][0]['has_effects']

def test_swiftui_scroll_transition_effects(swift_parser):
    """Test parsing of SwiftUI scroll transition effects."""
    code = """
    struct ScrollTransitionEffectsView: View {
        var body: some View {
            ScrollView {
                LazyVStack {
                    ForEach(0..<10) { index in
                        Text("Item \(index)")
                            .scrollTransition { content, phase in
                                content
                                    .opacity(phase.isIdentity ? 1 : 0)
                                    .scaleEffect(phase.isIdentity ? 1 : 0.8)
                                    .rotationEffect(.degrees(phase.isIdentity ? 0 : 45))
                                    .blur(radius: phase.isIdentity ? 0 : 10)
                            }
                    }
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ScrollTransitionEffectsView'
    assert len(view['scroll_transitions']) == 1
    assert view['scroll_transitions'][0]['has_effects']
    assert len(view['scroll_transitions'][0]['effects']) == 4
    assert all(effect in view['scroll_transitions'][0]['effects'] for effect in ['opacity', 'scaleEffect', 'rotationEffect', 'blur'])

def test_swiftui_scroll_transition_animation(swift_parser):
    """Test parsing of SwiftUI scroll transition animation."""
    code = """
    struct ScrollTransitionAnimationView: View {
        var body: some View {
            ScrollView {
                LazyVStack {
                    ForEach(0..<10) { index in
                        Text("Item \(index)")
                            .scrollTransition { content, phase in
                                content
                                    .opacity(phase.isIdentity ? 1 : 0)
                                    .scaleEffect(phase.isIdentity ? 1 : 0.8)
                            }
                            .animation(.spring(response: 0.5, dampingFraction: 0.6), value: phase.isIdentity)
                    }
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ScrollTransitionAnimationView'
    assert len(view['scroll_transitions']) == 1
    assert view['scroll_transitions'][0]['has_animation']
    assert view['scroll_transitions'][0]['animation_type'] == 'spring'
    assert view['scroll_transitions'][0]['has_animation_value']

def test_swiftui_scroll_transition_animation_curve(swift_parser):
    """Test parsing of SwiftUI scroll transition animation curve."""
    code = """
    struct ScrollTransitionAnimationCurveView: View {
        var body: some View {
            ScrollView {
                LazyVStack {
                    ForEach(0..<10) { index in
                        Text("Item \(index)")
                            .scrollTransition { content, phase in
                                content
                                    .opacity(phase.isIdentity ? 1 : 0)
                                    .scaleEffect(phase.isIdentity ? 1 : 0.8)
                            }
                            .animation(
                                .spring(response: 0.5, dampingFraction: 0.6)
                                .speed(1.2)
                                .repeatCount(2, autoreverses: true),
                                value: phase.isIdentity
                            )
                    }
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ScrollTransitionAnimationCurveView'
    assert len(view['scroll_transitions']) == 1
    assert view['scroll_transitions'][0]['has_animation']
    assert view['scroll_transitions'][0]['has_animation_curve']
    assert view['scroll_transitions'][0]['animation_curve']['has_speed']
    assert view['scroll_transitions'][0]['animation_curve']['has_repeat']

def test_swiftui_scroll_transition_animation_curve_priority(swift_parser):
    """Test parsing of SwiftUI scroll transition animation curve priority."""
    code = """
    struct ScrollTransitionAnimationCurvePriorityView: View {
        var body: some View {
            ScrollView {
                LazyVStack {
                    ForEach(0..<10) { index in
                        Text("Item \(index)")
                            .scrollTransition { content, phase in
                                content
                                    .opacity(phase.isIdentity ? 1 : 0)
                                    .scaleEffect(phase.isIdentity ? 1 : 0.8)
                            }
                            .animation(
                                .spring(response: 0.5, dampingFraction: 0.6)
                                .speed(1.2)
                                .repeatCount(2, autoreverses: true)
                                .priority(.high),
                                value: phase.isIdentity
                            )
                    }
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ScrollTransitionAnimationCurvePriorityView'
    assert len(view['scroll_transitions']) == 1
    assert view['scroll_transitions'][0]['has_animation']
    assert view['scroll_transitions'][0]['has_animation_curve']
    assert view['scroll_transitions'][0]['animation_curve']['has_priority']
    assert view['scroll_transitions'][0]['animation_curve']['priority'] == 'high'

def test_swiftui_charts(swift_parser):
    """Test parsing of SwiftUI charts."""
    code = """
    struct ChartView: View {
        let data = [1.0, 2.0, 3.0, 4.0, 5.0]
        
        var body: some View {
            Chart {
                ForEach(data, id: \\.self) { value in
                    LineMark(
                        x: .value("Index", data.firstIndex(of: value)!),
                        y: .value("Value", value)
                    )
                    .foregroundStyle(.blue)
                }
            }
            .chartXAxis {
                AxisMarks(values: .automatic)
            }
            .chartYAxis {
                AxisMarks(values: .automatic)
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ChartView'
    assert len(view['charts']) == 1
    assert view['charts'][0]['has_marks']
    assert view['charts'][0]['has_axes']

def test_swiftui_canvas(swift_parser):
    """Test parsing of SwiftUI canvas."""
    code = """
    struct CanvasView: View {
        var body: some View {
            Canvas { context, size in
                context.fill(
                    Path(ellipseIn: CGRect(x: 0, y: 0, width: size.width, height: size.height)),
                    with: .color(.blue)
                )
            }
            .frame(width: 200, height: 200)
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'CanvasView'
    assert len(view['canvases']) == 1
    assert view['canvases'][0]['has_context']
    assert view['canvases'][0]['has_size']

def test_swiftui_timeline_view(swift_parser):
    """Test parsing of SwiftUI timeline view."""
    code = """
    struct TimelineView: View {
        var body: some View {
            TimelineView(.animation) { timeline in
                Text("Current time: \(timeline.date)")
                    .font(.title)
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'TimelineView'
    assert len(view['timeline_views']) == 1
    assert view['timeline_views'][0]['has_schedule']
    assert view['timeline_views'][0]['has_context']

def test_swiftui_share_link(swift_parser):
    """Test parsing of SwiftUI share link."""
    code = """
    struct ShareLinkView: View {
        let text = "Check out this amazing app!"
        let url = URL(string: "https://example.com")!
        
        var body: some View {
            ShareLink(
                item: text,
                subject: Text("App Recommendation"),
                message: Text("I thought you might like this app"),
                preview: SharePreview(
                    "App Name",
                    image: Image(systemName: "star")
                )
            )
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ShareLinkView'
    assert len(view['share_links']) == 1
    assert view['share_links'][0]['has_preview']
    assert view['share_links'][0]['has_subject']

def test_swiftui_photos_picker(swift_parser):
    """Test parsing of SwiftUI photos picker."""
    code = """
    struct PhotosPickerView: View {
        @State private var selectedItem: PhotosPickerItem?
        @State private var selectedImage: Image?
        
        var body: some View {
            PhotosPicker(
                selection: $selectedItem,
                matching: .images,
                photoLibrary: .shared()
            ) {
                Label("Select Image", systemImage: "photo")
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'PhotosPickerView'
    assert len(view['photos_pickers']) == 1
    assert view['photos_pickers'][0]['has_selection']
    assert view['photos_pickers'][0]['has_matching']

def test_swiftui_camera(swift_parser):
    """Test parsing of SwiftUI camera."""
    code = """
    struct CameraView: View {
        @StateObject private var camera = CameraModel()
        
        var body: some View {
            ZStack {
                CameraPreview(camera: camera)
                    .ignoresSafeArea()
                
                VStack {
                    Spacer()
                    Button("Take Photo") {
                        camera.takePicture()
                    }
                    .padding()
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'CameraView'
    assert len(view['cameras']) == 1
    assert view['cameras'][0]['has_preview']
    assert view['cameras'][0]['has_controls']

def test_swiftui_location_button(swift_parser):
    """Test parsing of SwiftUI location button."""
    code = """
    struct LocationButtonView: View {
        @StateObject private var locationManager = LocationManager()
        
        var body: some View {
            LocationButton {
                locationManager.requestLocation()
            } label: {
                Label("Share Location", systemImage: "location")
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'LocationButtonView'
    assert len(view['location_buttons']) == 1
    assert view['location_buttons'][0]['has_action']
    assert view['location_buttons'][0]['has_label']

def test_swiftui_activity_indicator(swift_parser):
    """Test parsing of SwiftUI activity indicator."""
    code = """
    struct ActivityIndicatorView: View {
        @State private var isLoading = true
        
        var body: some View {
            if isLoading {
                ProgressView()
                    .progressViewStyle(CircularProgressViewStyle())
                    .scaleEffect(1.5)
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ActivityIndicatorView'
    assert len(view['progress_views']) == 1
    assert view['progress_views'][0]['has_style']
    assert view['progress_views'][0]['has_scale']

def test_swiftui_refreshable(swift_parser):
    """Test parsing of SwiftUI refreshable modifier."""
    code = """
    struct RefreshableView: View {
        @State private var items: [String] = []
        
        var body: some View {
            List(items, id: \\.self) { item in
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
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'RefreshableView'
    assert len(view['refreshable_views']) == 1
    assert view['refreshable_views'][0]['has_action']
    assert view['refreshable_views'][0]['action_is_async']

def test_swiftui_searchable(swift_parser):
    """Test parsing of SwiftUI searchable modifier."""
    code = """
    struct SearchableView: View {
        @State private var searchText = ""
        @State private var items: [String] = []
        
        var body: some View {
            List(filteredItems, id: \\.self) { item in
                Text(item)
            }
            .searchable(text: $searchText, prompt: "Search items")
        }
        
        var filteredItems: [String] {
            if searchText.isEmpty {
                return items
            }
            return items.filter { $0.localizedCaseInsensitiveContains(searchText) }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'SearchableView'
    assert len(view['searchable_views']) == 1
    assert view['searchable_views'][0]['has_text']
    assert view['searchable_views'][0]['has_prompt']

def test_swiftui_toolbar_placement(swift_parser):
    """Test parsing of SwiftUI toolbar placement."""
    code = """
    struct ToolbarPlacementView: View {
        var body: some View {
            NavigationView {
                Text("Content")
                    .toolbar {
                        ToolbarItem(placement: .navigationBarLeading) {
                            Button("Leading") { }
                        }
                        ToolbarItem(placement: .navigationBarTrailing) {
                            Button("Trailing") { }
                        }
                        ToolbarItem(placement: .bottomBar) {
                            Button("Bottom") { }
                        }
                    }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ToolbarPlacementView'
    assert len(view['toolbar_items']) == 3
    assert any(item['placement'] == 'navigationBarLeading' for item in view['toolbar_items'])
    assert any(item['placement'] == 'navigationBarTrailing' for item in view['toolbar_items'])
    assert any(item['placement'] == 'bottomBar' for item in view['toolbar_items'])

def test_swiftui_safe_area(swift_parser):
    """Test parsing of SwiftUI safe area handling."""
    code = """
    struct SafeAreaView: View {
        var body: some View {
            ZStack {
                Color.blue
                    .ignoresSafeArea()
                
                VStack {
                    Text("Content")
                        .padding()
                }
                .safeAreaInset(edge: .bottom) {
                    Color.red
                        .frame(height: 50)
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'SafeAreaView'
    assert len(view['safe_area_insets']) == 1
    assert view['safe_area_insets'][0]['edge'] == 'bottom'
    assert any(node['ignores_safe_area'] for node in view['nodes'])

def test_swiftui_scene_storage(swift_parser):
    """Test parsing of SwiftUI scene storage."""
    code = """
    struct SceneStorageView: View {
        @SceneStorage("selectedTab") private var selectedTab = 0
        
        var body: some View {
            TabView(selection: $selectedTab) {
                Text("Tab 1")
                    .tag(0)
                Text("Tab 2")
                    .tag(1)
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'SceneStorageView'
    assert len(view['scene_storage']) == 1
    assert view['scene_storage'][0]['key'] == 'selectedTab'
    assert view['scene_storage'][0]['has_default_value']

def test_swiftui_app_storage(swift_parser):
    """Test parsing of SwiftUI app storage."""
    code = """
    struct AppStorageView: View {
        @AppStorage("username") private var username = ""
        @AppStorage("isDarkMode") private var isDarkMode = false
        
        var body: some View {
            VStack {
                TextField("Username", text: $username)
                Toggle("Dark Mode", isOn: $isDarkMode)
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'AppStorageView'
    assert len(view['app_storage']) == 2
    assert any(storage['key'] == 'username' for storage in view['app_storage'])
    assert any(storage['key'] == 'isDarkMode' for storage in view['app_storage'])

def test_swiftui_focus_state(swift_parser):
    """Test parsing of SwiftUI focus state."""
    code = """
    struct FocusStateView: View {
        @FocusState private var isFocused: Bool
        
        var body: some View {
            TextField("Enter text", text: .constant(""))
                .focused($isFocused)
                .onChange(of: isFocused) { newValue in
                    print("Focus changed: \(newValue)")
                }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'FocusStateView'
    assert len(view['focus_states']) == 1
    assert view['focus_states'][0]['has_binding']
    assert view['focus_states'][0]['has_on_change']

def test_swiftui_scroll_target(swift_parser):
    """Test parsing of SwiftUI scroll target."""
    code = """
    struct ScrollTargetView: View {
        @State private var scrollPosition: Int?
        
        var body: some View {
            ScrollView {
                LazyVStack {
                    ForEach(0..<10) { index in
                        Text("Item \(index)")
                            .scrollTransition { content, phase in
                                content
                                    .opacity(phase.isIdentity ? 1 : 0)
                            }
                    }
                }
            }
            .scrollTargetBehavior(.viewAligned)
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ScrollTargetView'
    assert len(view['scroll_targets']) == 1
    assert view['scroll_targets'][0]['behavior'] == 'viewAligned'
    assert view['scroll_targets'][0]['has_transition']

def test_swiftui_scroll_indicator(swift_parser):
    """Test parsing of SwiftUI scroll indicator."""
    code = """
    struct ScrollIndicatorView: View {
        var body: some View {
            ScrollView {
                LazyVStack {
                    ForEach(0..<10) { index in
                        Text("Item \(index)")
                    }
                }
            }
            .scrollIndicators(.hidden)
            .scrollIndicatorsFlash(trigger: true)
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ScrollIndicatorView'
    assert len(view['scroll_indicators']) == 1
    assert view['scroll_indicators'][0]['visibility'] == 'hidden'
    assert view['scroll_indicators'][0]['has_flash']

def test_swiftui_scroll_clip_disabled(swift_parser):
    """Test parsing of SwiftUI scroll clip disabled."""
    code = """
    struct ScrollClipDisabledView: View {
        var body: some View {
            ScrollView {
                VStack {
                    ForEach(0..<10) { index in
                        Text("Item \(index)")
                            .frame(height: 100)
                    }
                }
            }
            .scrollClipDisabled()
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ScrollClipDisabledView'
    assert view['scroll_clip_disabled']

def test_swiftui_scroll_position(swift_parser):
    """Test parsing of SwiftUI scroll position."""
    code = """
    struct ScrollPositionView: View {
        @State private var scrollPosition: Int?
        
        var body: some View {
            ScrollView {
                LazyVStack {
                    ForEach(0..<10) { index in
                        Text("Item \(index)")
                    }
                }
            }
            .scrollPosition(id: $scrollPosition)
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ScrollPositionView'
    assert len(view['scroll_positions']) == 1
    assert view['scroll_positions'][0]['has_binding']
    assert view['scroll_positions'][0]['binding_type'] == 'id'

def test_swiftui_scroll_target_behavior(swift_parser):
    """Test parsing of SwiftUI scroll target behavior."""
    code = """
    struct ScrollTargetBehaviorView: View {
        var body: some View {
            ScrollView {
                LazyVStack {
                    ForEach(0..<10) { index in
                        Text("Item \(index)")
                    }
                }
            }
            .scrollTargetBehavior(.viewAligned)
            .scrollTargetLayout()
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ScrollTargetBehaviorView'
    assert len(view['scroll_target_behaviors']) == 1
    assert view['scroll_target_behaviors'][0]['behavior'] == 'viewAligned'
    assert view['scroll_target_behaviors'][0]['has_layout']

def test_swiftui_scroll_transition(swift_parser):
    """Test parsing of SwiftUI scroll transition."""
    code = """
    struct ScrollTransitionView: View {
        var body: some View {
            ScrollView {
                LazyVStack {
                    ForEach(0..<10) { index in
                        Text("Item \(index)")
                            .scrollTransition { content, phase in
                                content
                                    .opacity(phase.isIdentity ? 1 : 0)
                                    .scaleEffect(phase.isIdentity ? 1 : 0.8)
                            }
                    }
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ScrollTransitionView'
    assert len(view['scroll_transitions']) == 1
    assert view['scroll_transitions'][0]['has_phase']
    assert view['scroll_transitions'][0]['has_content']
    assert view['scroll_transitions'][0]['has_effects']

def test_swiftui_scroll_transition_phase(swift_parser):
    """Test parsing of SwiftUI scroll transition phase."""
    code = """
    struct ScrollTransitionPhaseView: View {
        var body: some View {
            ScrollView {
                LazyVStack {
                    ForEach(0..<10) { index in
                        Text("Item \(index)")
                            .scrollTransition { content, phase in
                                content
                                    .opacity(phase.isIdentity ? 1 : 0)
                                    .scaleEffect(phase.isIdentity ? 1 : 0.8)
                                    .rotationEffect(.degrees(phase.isIdentity ? 0 : 45))
                            }
                    }
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ScrollTransitionPhaseView'
    assert len(view['scroll_transitions']) == 1
    assert view['scroll_transitions'][0]['has_phase']
    assert view['scroll_transitions'][0]['has_identity_check']
    assert view['scroll_transitions'][0]['has_effects']

def test_swiftui_scroll_transition_effects(swift_parser):
    """Test parsing of SwiftUI scroll transition effects."""
    code = """
    struct ScrollTransitionEffectsView: View {
        var body: some View {
            ScrollView {
                LazyVStack {
                    ForEach(0..<10) { index in
                        Text("Item \(index)")
                            .scrollTransition { content, phase in
                                content
                                    .opacity(phase.isIdentity ? 1 : 0)
                                    .scaleEffect(phase.isIdentity ? 1 : 0.8)
                                    .rotationEffect(.degrees(phase.isIdentity ? 0 : 45))
                                    .blur(radius: phase.isIdentity ? 0 : 10)
                            }
                    }
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ScrollTransitionEffectsView'
    assert len(view['scroll_transitions']) == 1
    assert view['scroll_transitions'][0]['has_effects']
    assert len(view['scroll_transitions'][0]['effects']) == 4
    assert all(effect in view['scroll_transitions'][0]['effects'] for effect in ['opacity', 'scaleEffect', 'rotationEffect', 'blur'])

def test_swiftui_scroll_transition_animation(swift_parser):
    """Test parsing of SwiftUI scroll transition animation."""
    code = """
    struct ScrollTransitionAnimationView: View {
        var body: some View {
            ScrollView {
                LazyVStack {
                    ForEach(0..<10) { index in
                        Text("Item \(index)")
                            .scrollTransition { content, phase in
                                content
                                    .opacity(phase.isIdentity ? 1 : 0)
                                    .scaleEffect(phase.isIdentity ? 1 : 0.8)
                            }
                            .animation(.spring(response: 0.5, dampingFraction: 0.6), value: phase.isIdentity)
                    }
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ScrollTransitionAnimationView'
    assert len(view['scroll_transitions']) == 1
    assert view['scroll_transitions'][0]['has_animation']
    assert view['scroll_transitions'][0]['animation_type'] == 'spring'
    assert view['scroll_transitions'][0]['has_animation_value']

def test_swiftui_scroll_transition_animation_curve(swift_parser):
    """Test parsing of SwiftUI scroll transition animation curve."""
    code = """
    struct ScrollTransitionAnimationCurveView: View {
        var body: some View {
            ScrollView {
                LazyVStack {
                    ForEach(0..<10) { index in
                        Text("Item \(index)")
                            .scrollTransition { content, phase in
                                content
                                    .opacity(phase.isIdentity ? 1 : 0)
                                    .scaleEffect(phase.isIdentity ? 1 : 0.8)
                            }
                            .animation(
                                .spring(response: 0.5, dampingFraction: 0.6)
                                .speed(1.2)
                                .repeatCount(2, autoreverses: true),
                                value: phase.isIdentity
                            )
                    }
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ScrollTransitionAnimationCurveView'
    assert len(view['scroll_transitions']) == 1
    assert view['scroll_transitions'][0]['has_animation']
    assert view['scroll_transitions'][0]['has_animation_curve']
    assert view['scroll_transitions'][0]['animation_curve']['has_speed']
    assert view['scroll_transitions'][0]['animation_curve']['has_repeat']

def test_swiftui_scroll_transition_animation_curve_priority(swift_parser):
    """Test parsing of SwiftUI scroll transition animation curve priority."""
    code = """
    struct ScrollTransitionAnimationCurvePriorityView: View {
        var body: some View {
            ScrollView {
                LazyVStack {
                    ForEach(0..<10) { index in
                        Text("Item \(index)")
                            .scrollTransition { content, phase in
                                content
                                    .opacity(phase.isIdentity ? 1 : 0)
                                    .scaleEffect(phase.isIdentity ? 1 : 0.8)
                            }
                            .animation(
                                .spring(response: 0.5, dampingFraction: 0.6)
                                .speed(1.2)
                                .repeatCount(2, autoreverses: true)
                                .priority(.high),
                                value: phase.isIdentity
                            )
                    }
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ScrollTransitionAnimationCurvePriorityView'
    assert len(view['scroll_transitions']) == 1
    assert view['scroll_transitions'][0]['has_animation']
    assert view['scroll_transitions'][0]['has_animation_curve']
    assert view['scroll_transitions'][0]['animation_curve']['has_priority']
    assert view['scroll_transitions'][0]['animation_curve']['priority'] == 'high'

def test_swift_error_handling(swift_parser):
    """Test parsing of Swift error handling with try-catch blocks."""
    code = """
    struct ErrorHandlingView: View {
        @State private var error: Error?
        
        func fetchData() async throws {
            guard let url = URL(string: "https://api.example.com/data") else {
                throw URLError(.badURL)
            }
            
            let (data, response) = try await URLSession.shared.data(from: url)
            
            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                throw URLError(.badServerResponse)
            }
            
            // Process data
        }
        
        var body: some View {
            VStack {
                Button("Fetch Data") {
                    Task {
                        do {
                            try await fetchData()
                        } catch URLError.badURL {
                            self.error = error
                        } catch URLError.badServerResponse {
                            self.error = error
                        } catch {
                            self.error = error
                        }
                    }
                }
                
                if let error = error {
                    Text(error.localizedDescription)
                        .foregroundColor(.red)
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ErrorHandlingView'
    assert len(view['error_handling']) == 1
    assert view['error_handling'][0]['has_try_catch']
    assert view['error_handling'][0]['has_async_throws']
    assert view['error_handling'][0]['has_error_propagation']

def test_swift_optional_handling(swift_parser):
    """Test parsing of Swift optional chaining and nil coalescing."""
    code = """
    struct OptionalHandlingView: View {
        @State private var user: User?
        @State private var settings: Settings?
        
        var body: some View {
            VStack {
                Text(user?.name ?? "Guest")
                    .font(.title)
                
                if let settings = settings {
                    Text(settings.theme)
                        .foregroundColor(settings.color)
                }
                
                Button("Load User") {
                    Task {
                        // Simulate network call
                        user = await fetchUser()
                        settings = user?.preferences?.settings ?? Settings.default
                    }
                }
            }
        }
        
        func fetchUser() async -> User? {
            // Implementation
            return nil
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'OptionalHandlingView'
    assert len(view['optional_handling']) == 1
    assert view['optional_handling'][0]['has_optional_chaining']
    assert view['optional_handling'][0]['has_nil_coalescing']
    assert view['optional_handling'][0]['has_optional_binding']

def test_swift_result_builders(swift_parser):
    """Test parsing of Swift result builders in SwiftUI."""
    code = """
    struct ResultBuilderView: View {
        @State private var items = ["Item 1", "Item 2", "Item 3"]
        
        var body: some View {
            VStack {
                ForEach(items, id: \\.self) { item in
                    Text(item)
                        .padding()
                        .background(Color.blue)
                        .foregroundColor(.white)
                        .cornerRadius(8)
                }
            }
            .padding()
        }
    }
    
    @resultBuilder
    struct CustomBuilder {
        static func buildBlock(_ components: String...) -> String {
            components.joined(separator: " ")
        }
    }
    
    func customView(@CustomBuilder content: () -> String) -> String {
        content()
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ResultBuilderView'
    assert len(view['result_builders']) == 1
    assert view['result_builders'][0]['has_custom_builder']
    assert view['result_builders'][0]['has_build_block']
    assert view['result_builders'][0]['has_builder_usage']

def test_swift_property_wrapper_custom(swift_parser):
    """Test parsing of custom property wrappers in SwiftUI."""
    code = """
    @propertyWrapper
    struct Clamped<Value: Comparable> {
        var wrappedValue: Value
        let range: ClosedRange<Value>
        
        init(wrappedValue: Value, range: ClosedRange<Value>) {
            self.wrappedValue = min(max(wrappedValue, range.lowerBound), range.upperBound)
            self.range = range
        }
    }
    
    struct CustomWrapperView: View {
        @Clamped(range: 0...100) private var progress: Double = 50
        @Clamped(range: 0...255) private var red: Double = 128
        @Clamped(range: 0...255) private var green: Double = 128
        @Clamped(range: 0...255) private var blue: Double = 128
        
        var body: some View {
            VStack {
                Slider(value: $progress, in: 0...100)
                Color(red: red/255, green: green/255, blue: blue/255)
                    .frame(height: 100)
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'CustomWrapperView'
    assert len(view['property_wrappers']) == 4
    assert all(wrapper['type'] == 'Clamped' for wrapper in view['property_wrappers'])
    assert all(wrapper['has_range'] for wrapper in view['property_wrappers'])

def test_swift_complex_view_hierarchy(swift_parser):
    """Test parsing of complex nested view hierarchies in SwiftUI."""
    code = """
    struct ComplexHierarchyView: View {
        @State private var selectedTab = 0
        @State private var isShowingSheet = false
        
        var body: some View {
            TabView(selection: $selectedTab) {
                NavigationView {
                    ScrollView {
                        LazyVStack(spacing: 16) {
                            ForEach(0..<10) { index in
                                VStack(alignment: .leading) {
                                    HStack {
                                        Image(systemName: "star.fill")
                                            .foregroundColor(.yellow)
                                        Text("Item \(index)")
                                            .font(.headline)
                                    }
                                    
                                    Text("Description \(index)")
                                        .font(.subheadline)
                                        .foregroundColor(.secondary)
                                }
                                .padding()
                                .background(Color(.systemBackground))
                                .cornerRadius(12)
                                .shadow(radius: 2)
                            }
                        }
                        .padding()
                    }
                    .navigationTitle("Complex View")
                    .toolbar {
                        ToolbarItem(placement: .navigationBarTrailing) {
                            Button(action: { isShowingSheet = true }) {
                                Image(systemName: "plus")
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
            .sheet(isPresented: $isShowingSheet) {
                NavigationView {
                    AddItemView()
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ComplexHierarchyView'
    assert len(view['nested_containers']) > 0
    assert view['has_tab_view']
    assert view['has_navigation_view']
    assert view['has_scroll_view']
    assert view['has_lazy_vstack']
    assert view['has_sheet']

def test_swift_invalid_view_hierarchy(swift_parser):
    """Test parsing of invalid SwiftUI view hierarchies."""
    code = """
    struct InvalidHierarchyView: View {
        var body: some View {
            // Invalid: Multiple root views
            Text("First")
            Text("Second")
            
            // Invalid: View inside non-View container
            VStack {
                Text("Valid")
                Button("Valid") { }
                // Invalid: View inside non-View
                if true {
                    Text("Invalid")
                }
            }
            
            // Invalid: Missing required parameters
            Image() // Missing required name parameter
            
            // Invalid: Incorrect binding
            TextField("Label", text: "Invalid") // Should be binding
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'InvalidHierarchyView'
    assert len(view['parsing_errors']) > 0
    assert any(error['type'] == 'multiple_root_views' for error in view['parsing_errors'])
    assert any(error['type'] == 'invalid_container' for error in view['parsing_errors'])
    assert any(error['type'] == 'missing_required_parameter' for error in view['parsing_errors'])
    assert any(error['type'] == 'invalid_binding' for error in view['parsing_errors'])

def test_swift_closures_and_captures(swift_parser):
    """Test parsing of Swift closures and capture lists."""
    code = """
    struct ClosureView: View {
        @State private var count = 0
        @State private var message = ""
        
        // Closure with capture list
        let increment = { [weak self] in
            guard let self = self else { return }
            self.count += 1
        }
        
        // Closure with multiple captures
        let updateMessage = { [weak self, count] in
            guard let self = self else { return }
            self.message = "Count is \(count)"
        }
        
        // Async closure
        let fetchData = { [weak self] async in
            guard let self = self else { return }
            // Simulate network call
            try? await Task.sleep(nanoseconds: 1_000_000_000)
            self.message = "Data fetched"
        }
        
        var body: some View {
            VStack {
                Text("Count: \(count)")
                Text(message)
                
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
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ClosureView'
    assert len(view['closures']) == 3
    assert all(closure['has_capture_list'] for closure in view['closures'])
    assert any(closure['is_async'] for closure in view['closures'])
    assert any(closure['has_weak_self'] for closure in view['closures'])

def test_swift_type_casting(swift_parser):
    """Test parsing of Swift type casting and type checking."""
    code = """
    struct TypeCastingView: View {
        @State private var items: [Any] = [
            "String",
            42,
            true,
            ["nested": "array"],
            User(name: "John")
        ]
        
        var body: some View {
            List(items, id: \\.self) { item in
                Group {
                    if let string = item as? String {
                        Text(string)
                    } else if let number = item as? Int {
                        Text("\(number)")
                    } else if let bool = item as? Bool {
                        Text(bool ? "True" : "False")
                    } else if let dict = item as? [String: String] {
                        Text(dict["nested"] ?? "")
                    } else if let user = item as? User {
                        Text(user.name)
                    }
                }
            }
        }
    }
    
    struct User {
        let name: String
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'TypeCastingView'
    assert len(view['type_casting']) == 5
    assert all(cast['has_type_check'] for cast in view['type_casting'])
    assert all(cast['has_optional_cast'] for cast in view['type_casting'])
    assert view['has_heterogeneous_array']

def test_swift_error_handling(swift_parser):
    """Test parsing of Swift error handling with try-catch blocks."""
    code = """
    struct ErrorHandlingView: View {
        @State private var error: Error?
        
        func fetchData() async throws {
            guard let url = URL(string: "https://api.example.com/data") else {
                throw URLError(.badURL)
            }
            
            let (data, response) = try await URLSession.shared.data(from: url)
            
            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                throw URLError(.badServerResponse)
            }
            
            // Process data
        }
        
        var body: some View {
            VStack {
                Button("Fetch Data") {
                    Task {
                        do {
                            try await fetchData()
                        } catch URLError.badURL {
                            self.error = error
                        } catch URLError.badServerResponse {
                            self.error = error
                        } catch {
                            self.error = error
                        }
                    }
                }
                
                if let error = error {
                    Text(error.localizedDescription)
                        .foregroundColor(.red)
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ErrorHandlingView'
    assert len(view['error_handling']) == 1
    assert view['error_handling'][0]['has_try_catch']
    assert view['error_handling'][0]['has_async_throws']
    assert view['error_handling'][0]['has_error_propagation']

def test_swift_optional_handling(swift_parser):
    """Test parsing of Swift optional chaining and nil coalescing."""
    code = """
    struct OptionalHandlingView: View {
        @State private var user: User?
        @State private var settings: Settings?
        
        var body: some View {
            VStack {
                Text(user?.name ?? "Guest")
                    .font(.title)
                
                if let settings = settings {
                    Text(settings.theme)
                        .foregroundColor(settings.color)
                }
                
                Button("Load User") {
                    Task {
                        // Simulate network call
                        user = await fetchUser()
                        settings = user?.preferences?.settings ?? Settings.default
                    }
                }
            }
        }
        
        func fetchUser() async -> User? {
            // Implementation
            return nil
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'OptionalHandlingView'
    assert len(view['optional_handling']) == 1
    assert view['optional_handling'][0]['has_optional_chaining']
    assert view['optional_handling'][0]['has_nil_coalescing']
    assert view['optional_handling'][0]['has_optional_binding']

def test_swift_result_builders(swift_parser):
    """Test parsing of Swift result builders in SwiftUI."""
    code = """
    struct ResultBuilderView: View {
        @State private var items = ["Item 1", "Item 2", "Item 3"]
        
        var body: some View {
            VStack {
                ForEach(items, id: \\.self) { item in
                    Text(item)
                        .padding()
                        .background(Color.blue)
                        .foregroundColor(.white)
                        .cornerRadius(8)
                }
            }
            .padding()
        }
    }
    
    @resultBuilder
    struct CustomBuilder {
        static func buildBlock(_ components: String...) -> String {
            components.joined(separator: " ")
        }
    }
    
    func customView(@CustomBuilder content: () -> String) -> String {
        content()
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ResultBuilderView'
    assert len(view['result_builders']) == 1
    assert view['result_builders'][0]['has_custom_builder']
    assert view['result_builders'][0]['has_build_block']
    assert view['result_builders'][0]['has_builder_usage']

def test_swift_property_wrapper_custom(swift_parser):
    """Test parsing of custom property wrappers in SwiftUI."""
    code = """
    @propertyWrapper
    struct Clamped<Value: Comparable> {
        var wrappedValue: Value
        let range: ClosedRange<Value>
        
        init(wrappedValue: Value, range: ClosedRange<Value>) {
            self.wrappedValue = min(max(wrappedValue, range.lowerBound), range.upperBound)
            self.range = range
        }
    }
    
    struct CustomWrapperView: View {
        @Clamped(range: 0...100) private var progress: Double = 50
        @Clamped(range: 0...255) private var red: Double = 128
        @Clamped(range: 0...255) private var green: Double = 128
        @Clamped(range: 0...255) private var blue: Double = 128
        
        var body: some View {
            VStack {
                Slider(value: $progress, in: 0...100)
                Color(red: red/255, green: green/255, blue: blue/255)
                    .frame(height: 100)
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'CustomWrapperView'
    assert len(view['property_wrappers']) == 4
    assert all(wrapper['type'] == 'Clamped' for wrapper in view['property_wrappers'])
    assert all(wrapper['has_range'] for wrapper in view['property_wrappers'])

def test_swift_complex_view_hierarchy(swift_parser):
    """Test parsing of complex nested view hierarchies in SwiftUI."""
    code = """
    struct ComplexHierarchyView: View {
        @State private var selectedTab = 0
        @State private var isShowingSheet = false
        
        var body: some View {
            TabView(selection: $selectedTab) {
                NavigationView {
                    ScrollView {
                        LazyVStack(spacing: 16) {
                            ForEach(0..<10) { index in
                                VStack(alignment: .leading) {
                                    HStack {
                                        Image(systemName: "star.fill")
                                            .foregroundColor(.yellow)
                                        Text("Item \(index)")
                                            .font(.headline)
                                    }
                                    
                                    Text("Description \(index)")
                                        .font(.subheadline)
                                        .foregroundColor(.secondary)
                                }
                                .padding()
                                .background(Color(.systemBackground))
                                .cornerRadius(12)
                                .shadow(radius: 2)
                            }
                        }
                        .padding()
                    }
                    .navigationTitle("Complex View")
                    .toolbar {
                        ToolbarItem(placement: .navigationBarTrailing) {
                            Button(action: { isShowingSheet = true }) {
                                Image(systemName: "plus")
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
            .sheet(isPresented: $isShowingSheet) {
                NavigationView {
                    AddItemView()
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ComplexHierarchyView'
    assert len(view['nested_containers']) > 0
    assert view['has_tab_view']
    assert view['has_navigation_view']
    assert view['has_scroll_view']
    assert view['has_lazy_vstack']
    assert view['has_sheet']

def test_swift_invalid_view_hierarchy(swift_parser):
    """Test parsing of invalid SwiftUI view hierarchies."""
    code = """
    struct InvalidHierarchyView: View {
        var body: some View {
            // Invalid: Multiple root views
            Text("First")
            Text("Second")
            
            // Invalid: View inside non-View container
            VStack {
                Text("Valid")
                Button("Valid") { }
                // Invalid: View inside non-View
                if true {
                    Text("Invalid")
                }
            }
            
            // Invalid: Missing required parameters
            Image() // Missing required name parameter
            
            // Invalid: Incorrect binding
            TextField("Label", text: "Invalid") // Should be binding
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'InvalidHierarchyView'
    assert len(view['parsing_errors']) > 0
    assert any(error['type'] == 'multiple_root_views' for error in view['parsing_errors'])
    assert any(error['type'] == 'invalid_container' for error in view['parsing_errors'])
    assert any(error['type'] == 'missing_required_parameter' for error in view['parsing_errors'])
    assert any(error['type'] == 'invalid_binding' for error in view['parsing_errors'])

def test_swift_closures_and_captures(swift_parser):
    """Test parsing of Swift closures and capture lists."""
    code = """
    struct ClosureView: View {
        @State private var count = 0
        @State private var message = ""
        
        // Closure with capture list
        let increment = { [weak self] in
            guard let self = self else { return }
            self.count += 1
        }
        
        // Closure with multiple captures
        let updateMessage = { [weak self, count] in
            guard let self = self else { return }
            self.message = "Count is \(count)"
        }
        
        // Async closure
        let fetchData = { [weak self] async in
            guard let self = self else { return }
            // Simulate network call
            try? await Task.sleep(nanoseconds: 1_000_000_000)
            self.message = "Data fetched"
        }
        
        var body: some View {
            VStack {
                Text("Count: \(count)")
                Text(message)
                
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
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ClosureView'
    assert len(view['closures']) == 3
    assert all(closure['has_capture_list'] for closure in view['closures'])
    assert any(closure['is_async'] for closure in view['closures'])
    assert any(closure['has_weak_self'] for closure in view['closures'])

def test_swift_type_casting(swift_parser):
    """Test parsing of Swift type casting and type checking."""
    code = """
    struct TypeCastingView: View {
        @State private var items: [Any] = [
            "String",
            42,
            true,
            ["nested": "array"],
            User(name: "John")
        ]
        
        var body: some View {
            List(items, id: \\.self) { item in
                Group {
                    if let string = item as? String {
                        Text(string)
                    } else if let number = item as? Int {
                        Text("\(number)")
                    } else if let bool = item as? Bool {
                        Text(bool ? "True" : "False")
                    } else if let dict = item as? [String: String] {
                        Text(dict["nested"] ?? "")
                    } else if let user = item as? User {
                        Text(user.name)
                    }
                }
            }
        }
    }
    
    struct User {
        let name: String
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'TypeCastingView'
    assert len(view['type_casting']) == 5
    assert all(cast['has_type_check'] for cast in view['type_casting'])
    assert all(cast['has_optional_cast'] for cast in view['type_casting'])
    assert view['has_heterogeneous_array']

def test_swift_error_handling(swift_parser):
    """Test parsing of Swift error handling with try-catch blocks."""
    code = """
    struct ErrorHandlingView: View {
        @State private var error: Error?
        
        func fetchData() async throws {
            guard let url = URL(string: "https://api.example.com/data") else {
                throw URLError(.badURL)
            }
            
            let (data, response) = try await URLSession.shared.data(from: url)
            
            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                throw URLError(.badServerResponse)
            }
            
            // Process data
        }
        
        var body: some View {
            VStack {
                Button("Fetch Data") {
                    Task {
                        do {
                            try await fetchData()
                        } catch URLError.badURL {
                            self.error = error
                        } catch URLError.badServerResponse {
                            self.error = error
                        } catch {
                            self.error = error
                        }
                    }
                }
                
                if let error = error {
                    Text(error.localizedDescription)
                        .foregroundColor(.red)
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ErrorHandlingView'
    assert len(view['error_handling']) == 1
    assert view['error_handling'][0]['has_try_catch']
    assert view['error_handling'][0]['has_async_throws']
    assert view['error_handling'][0]['has_error_propagation']

def test_swift_optional_handling(swift_parser):
    """Test parsing of Swift optional chaining and nil coalescing."""
    code = """
    struct OptionalHandlingView: View {
        @State private var user: User?
        @State private var settings: Settings?
        
        var body: some View {
            VStack {
                Text(user?.name ?? "Guest")
                    .font(.title)
                
                if let settings = settings {
                    Text(settings.theme)
                        .foregroundColor(settings.color)
                }
                
                Button("Load User") {
                    Task {
                        // Simulate network call
                        user = await fetchUser()
                        settings = user?.preferences?.settings ?? Settings.default
                    }
                }
            }
        }
        
        func fetchUser() async -> User? {
            // Implementation
            return nil
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'OptionalHandlingView'
    assert len(view['optional_handling']) == 1
    assert view['optional_handling'][0]['has_optional_chaining']
    assert view['optional_handling'][0]['has_nil_coalescing']
    assert view['optional_handling'][0]['has_optional_binding']

def test_swift_result_builders(swift_parser):
    """Test parsing of Swift result builders in SwiftUI."""
    code = """
    struct ResultBuilderView: View {
        @State private var items = ["Item 1", "Item 2", "Item 3"]
        
        var body: some View {
            VStack {
                ForEach(items, id: \\.self) { item in
                    Text(item)
                        .padding()
                        .background(Color.blue)
                        .foregroundColor(.white)
                        .cornerRadius(8)
                }
            }
            .padding()
        }
    }
    
    @resultBuilder
    struct CustomBuilder {
        static func buildBlock(_ components: String...) -> String {
            components.joined(separator: " ")
        }
    }
    
    func customView(@CustomBuilder content: () -> String) -> String {
        content()
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ResultBuilderView'
    assert len(view['result_builders']) == 1
    assert view['result_builders'][0]['has_custom_builder']
    assert view['result_builders'][0]['has_build_block']
    assert view['result_builders'][0]['has_builder_usage']

def test_swift_property_wrapper_custom(swift_parser):
    """Test parsing of custom property wrappers in SwiftUI."""
    code = """
    @propertyWrapper
    struct Clamped<Value: Comparable> {
        var wrappedValue: Value
        let range: ClosedRange<Value>
        
        init(wrappedValue: Value, range: ClosedRange<Value>) {
            self.wrappedValue = min(max(wrappedValue, range.lowerBound), range.upperBound)
            self.range = range
        }
    }
    
    struct CustomWrapperView: View {
        @Clamped(range: 0...100) private var progress: Double = 50
        @Clamped(range: 0...255) private var red: Double = 128
        @Clamped(range: 0...255) private var green: Double = 128
        @Clamped(range: 0...255) private var blue: Double = 128
        
        var body: some View {
            VStack {
                Slider(value: $progress, in: 0...100)
                Color(red: red/255, green: green/255, blue: blue/255)
                    .frame(height: 100)
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'CustomWrapperView'
    assert len(view['property_wrappers']) == 4
    assert all(wrapper['type'] == 'Clamped' for wrapper in view['property_wrappers'])
    assert all(wrapper['has_range'] for wrapper in view['property_wrappers'])

def test_swift_complex_view_hierarchy(swift_parser):
    """Test parsing of complex nested view hierarchies in SwiftUI."""
    code = """
    struct ComplexHierarchyView: View {
        @State private var selectedTab = 0
        @State private var isShowingSheet = false
        
        var body: some View {
            TabView(selection: $selectedTab) {
                NavigationView {
                    ScrollView {
                        LazyVStack(spacing: 16) {
                            ForEach(0..<10) { index in
                                VStack(alignment: .leading) {
                                    HStack {
                                        Image(systemName: "star.fill")
                                            .foregroundColor(.yellow)
                                        Text("Item \(index)")
                                            .font(.headline)
                                    }
                                    
                                    Text("Description \(index)")
                                        .font(.subheadline)
                                        .foregroundColor(.secondary)
                                }
                                .padding()
                                .background(Color(.systemBackground))
                                .cornerRadius(12)
                                .shadow(radius: 2)
                            }
                        }
                        .padding()
                    }
                    .navigationTitle("Complex View")
                    .toolbar {
                        ToolbarItem(placement: .navigationBarTrailing) {
                            Button(action: { isShowingSheet = true }) {
                                Image(systemName: "plus")
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
            .sheet(isPresented: $isShowingSheet) {
                NavigationView {
                    AddItemView()
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ComplexHierarchyView'
    assert len(view['nested_containers']) > 0
    assert view['has_tab_view']
    assert view['has_navigation_view']
    assert view['has_scroll_view']
    assert view['has_lazy_vstack']
    assert view['has_sheet']

def test_swift_invalid_view_hierarchy(swift_parser):
    """Test parsing of invalid SwiftUI view hierarchies."""
    code = """
    struct InvalidHierarchyView: View {
        var body: some View {
            // Invalid: Multiple root views
            Text("First")
            Text("Second")
            
            // Invalid: View inside non-View container
            VStack {
                Text("Valid")
                Button("Valid") { }
                // Invalid: View inside non-View
                if true {
                    Text("Invalid")
                }
            }
            
            // Invalid: Missing required parameters
            Image() // Missing required name parameter
            
            // Invalid: Incorrect binding
            TextField("Label", text: "Invalid") // Should be binding
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'InvalidHierarchyView'
    assert len(view['parsing_errors']) > 0
    assert any(error['type'] == 'multiple_root_views' for error in view['parsing_errors'])
    assert any(error['type'] == 'invalid_container' for error in view['parsing_errors'])
    assert any(error['type'] == 'missing_required_parameter' for error in view['parsing_errors'])
    assert any(error['type'] == 'invalid_binding' for error in view['parsing_errors'])

def test_swift_closures_and_captures(swift_parser):
    """Test parsing of Swift closures and capture lists."""
    code = """
    struct ClosureView: View {
        @State private var count = 0
        @State private var message = ""
        
        // Closure with capture list
        let increment = { [weak self] in
            guard let self = self else { return }
            self.count += 1
        }
        
        // Closure with multiple captures
        let updateMessage = { [weak self, count] in
            guard let self = self else { return }
            self.message = "Count is \(count)"
        }
        
        // Async closure
        let fetchData = { [weak self] async in
            guard let self = self else { return }
            // Simulate network call
            try? await Task.sleep(nanoseconds: 1_000_000_000)
            self.message = "Data fetched"
        }
        
        var body: some View {
            VStack {
                Text("Count: \(count)")
                Text(message)
                
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
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ClosureView'
    assert len(view['closures']) == 3
    assert all(closure['has_capture_list'] for closure in view['closures'])
    assert any(closure['is_async'] for closure in view['closures'])
    assert any(closure['has_weak_self'] for closure in view['closures'])

def test_swift_type_casting(swift_parser):
    """Test parsing of Swift type casting and type checking."""
    code = """
    struct TypeCastingView: View {
        @State private var items: [Any] = [
            "String",
            42,
            true,
            ["nested": "array"],
            User(name: "John")
        ]
        
        var body: some View {
            List(items, id: \\.self) { item in
                Group {
                    if let string = item as? String {
                        Text(string)
                    } else if let number = item as? Int {
                        Text("\(number)")
                    } else if let bool = item as? Bool {
                        Text(bool ? "True" : "False")
                    } else if let dict = item as? [String: String] {
                        Text(dict["nested"] ?? "")
                    } else if let user = item as? User {
                        Text(user.name)
                    }
                }
            }
        }
    }
    
    struct User {
        let name: String
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'TypeCastingView'
    assert len(view['type_casting']) == 5
    assert all(cast['has_type_check'] for cast in view['type_casting'])
    assert all(cast['has_optional_cast'] for cast in view['type_casting'])
    assert view['has_heterogeneous_array']

def test_swift_error_handling(swift_parser):
    """Test parsing of Swift error handling with try-catch blocks."""
    code = """
    struct ErrorHandlingView: View {
        @State private var error: Error?
        
        func fetchData() async throws {
            guard let url = URL(string: "https://api.example.com/data") else {
                throw URLError(.badURL)
            }
            
            let (data, response) = try await URLSession.shared.data(from: url)
            
            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                throw URLError(.badServerResponse)
            }
            
            // Process data
        }
        
        var body: some View {
            VStack {
                Button("Fetch Data") {
                    Task {
                        do {
                            try await fetchData()
                        } catch URLError.badURL {
                            self.error = error
                        } catch URLError.badServerResponse {
                            self.error = error
                        } catch {
                            self.error = error
                        }
                    }
                }
                
                if let error = error {
                    Text(error.localizedDescription)
                        .foregroundColor(.red)
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ErrorHandlingView'
    assert len(view['error_handling']) == 1
    assert view['error_handling'][0]['has_try_catch']
    assert view['error_handling'][0]['has_async_throws']
    assert view['error_handling'][0]['has_error_propagation']

def test_swift_optional_handling(swift_parser):
    """Test parsing of Swift optional chaining and nil coalescing."""
    code = """
    struct OptionalHandlingView: View {
        @State private var user: User?
        @State private var settings: Settings?
        
        var body: some View {
            VStack {
                Text(user?.name ?? "Guest")
                    .font(.title)
                
                if let settings = settings {
                    Text(settings.theme)
                        .foregroundColor(settings.color)
                }
                
                Button("Load User") {
                    Task {
                        // Simulate network call
                        user = await fetchUser()
                        settings = user?.preferences?.settings ?? Settings.default
                    }
                }
            }
        }
        
        func fetchUser() async -> User? {
            // Implementation
            return nil
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'OptionalHandlingView'
    assert len(view['optional_handling']) == 1
    assert view['optional_handling'][0]['has_optional_chaining']
    assert view['optional_handling'][0]['has_nil_coalescing']
    assert view['optional_handling'][0]['has_optional_binding']

def test_swift_result_builders(swift_parser):
    """Test parsing of Swift result builders in SwiftUI."""
    code = """
    struct ResultBuilderView: View {
        @State private var items = ["Item 1", "Item 2", "Item 3"]
        
        var body: some View {
            VStack {
                ForEach(items, id: \\.self) { item in
                    Text(item)
                        .padding()
                        .background(Color.blue)
                        .foregroundColor(.white)
                        .cornerRadius(8)
                }
            }
            .padding()
        }
    }
    
    @resultBuilder
    struct CustomBuilder {
        static func buildBlock(_ components: String...) -> String {
            components.joined(separator: " ")
        }
    }
    
    func customView(@CustomBuilder content: () -> String) -> String {
        content()
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ResultBuilderView'
    assert len(view['result_builders']) == 1
    assert view['result_builders'][0]['has_custom_builder']
    assert view['result_builders'][0]['has_build_block']
    assert view['result_builders'][0]['has_builder_usage']

def test_swift_property_wrapper_custom(swift_parser):
    """Test parsing of custom property wrappers in SwiftUI."""
    code = """
    @propertyWrapper
    struct Clamped<Value: Comparable> {
        var wrappedValue: Value
        let range: ClosedRange<Value>
        
        init(wrappedValue: Value, range: ClosedRange<Value>) {
            self.wrappedValue = min(max(wrappedValue, range.lowerBound), range.upperBound)
            self.range = range
        }
    }
    
    struct CustomWrapperView: View {
        @Clamped(range: 0...100) private var progress: Double = 50
        @Clamped(range: 0...255) private var red: Double = 128
        @Clamped(range: 0...255) private var green: Double = 128
        @Clamped(range: 0...255) private var blue: Double = 128
        
        var body: some View {
            VStack {
                Slider(value: $progress, in: 0...100)
                Color(red: red/255, green: green/255, blue: blue/255)
                    .frame(height: 100)
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'CustomWrapperView'
    assert len(view['property_wrappers']) == 4
    assert all(wrapper['type'] == 'Clamped' for wrapper in view['property_wrappers'])
    assert all(wrapper['has_range'] for wrapper in view['property_wrappers'])

def test_swift_complex_view_hierarchy(swift_parser):
    """Test parsing of complex nested view hierarchies in SwiftUI."""
    code = """
    struct ComplexHierarchyView: View {
        @State private var selectedTab = 0
        @State private var isShowingSheet = false
        
        var body: some View {
            TabView(selection: $selectedTab) {
                NavigationView {
                    ScrollView {
                        LazyVStack(spacing: 16) {
                            ForEach(0..<10) { index in
                                VStack(alignment: .leading) {
                                    HStack {
                                        Image(systemName: "star.fill")
                                            .foregroundColor(.yellow)
                                        Text("Item \(index)")
                                            .font(.headline)
                                    }
                                    
                                    Text("Description \(index)")
                                        .font(.subheadline)
                                        .foregroundColor(.secondary)
                                }
                                .padding()
                                .background(Color(.systemBackground))
                                .cornerRadius(12)
                                .shadow(radius: 2)
                            }
                        }
                        .padding()
                    }
                    .navigationTitle("Complex View")
                    .toolbar {
                        ToolbarItem(placement: .navigationBarTrailing) {
                            Button(action: { isShowingSheet = true }) {
                                Image(systemName: "plus")
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
            .sheet(isPresented: $isShowingSheet) {
                NavigationView {
                    AddItemView()
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ComplexHierarchyView'
    assert len(view['nested_containers']) > 0
    assert view['has_tab_view']
    assert view['has_navigation_view']
    assert view['has_scroll_view']
    assert view['has_lazy_vstack']
    assert view['has_sheet']

def test_swift_invalid_view_hierarchy(swift_parser):
    """Test parsing of invalid SwiftUI view hierarchies."""
    code = """
    struct InvalidHierarchyView: View {
        var body: some View {
            // Invalid: Multiple root views
            Text("First")
            Text("Second")
            
            // Invalid: View inside non-View container
            VStack {
                Text("Valid")
                Button("Valid") { }
                // Invalid: View inside non-View
                if true {
                    Text("Invalid")
                }
            }
            
            // Invalid: Missing required parameters
            Image() // Missing required name parameter
            
            // Invalid: Incorrect binding
            TextField("Label", text: "Invalid") // Should be binding
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'InvalidHierarchyView'
    assert len(view['parsing_errors']) > 0
    assert any(error['type'] == 'multiple_root_views' for error in view['parsing_errors'])
    assert any(error['type'] == 'invalid_container' for error in view['parsing_errors'])
    assert any(error['type'] == 'missing_required_parameter' for error in view['parsing_errors'])
    assert any(error['type'] == 'invalid_binding' for error in view['parsing_errors'])

def test_swift_closures_and_captures(swift_parser):
    """Test parsing of Swift closures and capture lists."""
    code = """
    struct ClosureView: View {
        @State private var count = 0
        @State private var message = ""
        
        // Closure with capture list
        let increment = { [weak self] in
            guard let self = self else { return }
            self.count += 1
        }
        
        // Closure with multiple captures
        let updateMessage = { [weak self, count] in
            guard let self = self else { return }
            self.message = "Count is \(count)"
        }
        
        // Async closure
        let fetchData = { [weak self] async in
            guard let self = self else { return }
            // Simulate network call
            try? await Task.sleep(nanoseconds: 1_000_000_000)
            self.message = "Data fetched"
        }
        
        var body: some View {
            VStack {
                Text("Count: \(count)")
                Text(message)
                
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
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ClosureView'
    assert len(view['closures']) == 3
    assert all(closure['has_capture_list'] for closure in view['closures'])
    assert any(closure['is_async'] for closure in view['closures'])
    assert any(closure['has_weak_self'] for closure in view['closures'])

def test_swift_type_casting(swift_parser):
    """Test parsing of Swift type casting and type checking."""
    code = """
    struct TypeCastingView: View {
        @State private var items: [Any] = [
            "String",
            42,
            true,
            ["nested": "array"],
            User(name: "John")
        ]
        
        var body: some View {
            List(items, id: \\.self) { item in
                Group {
                    if let string = item as? String {
                        Text(string)
                    } else if let number = item as? Int {
                        Text("\(number)")
                    } else if let bool = item as? Bool {
                        Text(bool ? "True" : "False")
                    } else if let dict = item as? [String: String] {
                        Text(dict["nested"] ?? "")
                    } else if let user = item as? User {
                        Text(user.name)
                    }
                }
            }
        }
    }
    
    struct User {
        let name: String
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'TypeCastingView'
    assert len(view['type_casting']) == 5
    assert all(cast['has_type_check'] for cast in view['type_casting'])
    assert all(cast['has_optional_cast'] for cast in view['type_casting'])
    assert view['has_heterogeneous_array']

def test_swift_error_handling(swift_parser):
    """Test parsing of Swift error handling with try-catch blocks."""
    code = """
    struct ErrorHandlingView: View {
        @State private var error: Error?
        
        func fetchData() async throws {
            guard let url = URL(string: "https://api.example.com/data") else {
                throw URLError(.badURL)
            }
            
            let (data, response) = try await URLSession.shared.data(from: url)
            
            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                throw URLError(.badServerResponse)
            }
            
            // Process data
        }
        
        var body: some View {
            VStack {
                Button("Fetch Data") {
                    Task {
                        do {
                            try await fetchData()
                        } catch URLError.badURL {
                            self.error = error
                        } catch URLError.badServerResponse {
                            self.error = error
                        } catch {
                            self.error = error
                        }
                    }
                }
                
                if let error = error {
                    Text(error.localizedDescription)
                        .foregroundColor(.red)
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ErrorHandlingView'
    assert len(view['error_handling']) == 1
    assert view['error_handling'][0]['has_try_catch']
    assert view['error_handling'][0]['has_async_throws']
    assert view['error_handling'][0]['has_error_propagation']

def test_swift_optional_handling(swift_parser):
    """Test parsing of Swift optional chaining and nil coalescing."""
    code = """
    struct OptionalHandlingView: View {
        @State private var user: User?
        @State private var settings: Settings?
        
        var body: some View {
            VStack {
                Text(user?.name ?? "Guest")
                    .font(.title)
                
                if let settings = settings {
                    Text(settings.theme)
                        .foregroundColor(settings.color)
                }
                
                Button("Load User") {
                    Task {
                        // Simulate network call
                        user = await fetchUser()
                        settings = user?.preferences?.settings ?? Settings.default
                    }
                }
            }
        }
        
        func fetchUser() async -> User? {
            // Implementation
            return nil
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'OptionalHandlingView'
    assert len(view['optional_handling']) == 1
    assert view['optional_handling'][0]['has_optional_chaining']
    assert view['optional_handling'][0]['has_nil_coalescing']
    assert view['optional_handling'][0]['has_optional_binding']

def test_swift_result_builders(swift_parser):
    """Test parsing of Swift result builders in SwiftUI."""
    code = """
    struct ResultBuilderView: View {
        @State private var items = ["Item 1", "Item 2", "Item 3"]
        
        var body: some View {
            VStack {
                ForEach(items, id: \\.self) { item in
                    Text(item)
                        .padding()
                        .background(Color.blue)
                        .foregroundColor(.white)
                        .cornerRadius(8)
                }
            }
            .padding()
        }
    }
    
    @resultBuilder
    struct CustomBuilder {
        static func buildBlock(_ components: String...) -> String {
            components.joined(separator: " ")
        }
    }
    
    func customView(@CustomBuilder content: () -> String) -> String {
        content()
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ResultBuilderView'
    assert len(view['result_builders']) == 1
    assert view['result_builders'][0]['has_custom_builder']
    assert view['result_builders'][0]['has_build_block']
    assert view['result_builders'][0]['has_builder_usage']

def test_swift_property_wrapper_custom(swift_parser):
    """Test parsing of custom property wrappers in SwiftUI."""
    code = """
    @propertyWrapper
    struct Clamped<Value: Comparable> {
        var wrappedValue: Value
        let range: ClosedRange<Value>
        
        init(wrappedValue: Value, range: ClosedRange<Value>) {
            self.wrappedValue = min(max(wrappedValue, range.lowerBound), range.upperBound)
            self.range = range
        }
    }
    
    struct CustomWrapperView: View {
        @Clamped(range: 0...100) private var progress: Double = 50
        @Clamped(range: 0...255) private var red: Double = 128
        @Clamped(range: 0...255) private var green: Double = 128
        @Clamped(range: 0...255) private var blue: Double = 128
        
        var body: some View {
            VStack {
                Slider(value: $progress, in: 0...100)
                Color(red: red/255, green: green/255, blue: blue/255)
                    .frame(height: 100)
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'CustomWrapperView'
    assert len(view['property_wrappers']) == 4
    assert all(wrapper['type'] == 'Clamped' for wrapper in view['property_wrappers'])
    assert all(wrapper['has_range'] for wrapper in view['property_wrappers'])

def test_swift_complex_view_hierarchy(swift_parser):
    """Test parsing of complex nested view hierarchies in SwiftUI."""
    code = """
    struct ComplexHierarchyView: View {
        @State private var selectedTab = 0
        @State private var isShowingSheet = false
        
        var body: some View {
            TabView(selection: $selectedTab) {
                NavigationView {
                    ScrollView {
                        LazyVStack(spacing: 16) {
                            ForEach(0..<10) { index in
                                VStack(alignment: .leading) {
                                    HStack {
                                        Image(systemName: "star.fill")
                                            .foregroundColor(.yellow)
                                        Text("Item \(index)")
                                            .font(.headline)
                                    }
                                    
                                    Text("Description \(index)")
                                        .font(.subheadline)
                                        .foregroundColor(.secondary)
                                }
                                .padding()
                                .background(Color(.systemBackground))
                                .cornerRadius(12)
                                .shadow(radius: 2)
                            }
                        }
                        .padding()
                    }
                    .navigationTitle("Complex View")
                    .toolbar {
                        ToolbarItem(placement: .navigationBarTrailing) {
                            Button(action: { isShowingSheet = true }) {
                                Image(systemName: "plus")
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
            .sheet(isPresented: $isShowingSheet) {
                NavigationView {
                    AddItemView()
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ComplexHierarchyView'
    assert len(view['nested_containers']) > 0
    assert view['has_tab_view']
    assert view['has_navigation_view']
    assert view['has_scroll_view']
    assert view['has_lazy_vstack']
    assert view['has_sheet']

def test_swift_invalid_view_hierarchy(swift_parser):
    """Test parsing of invalid SwiftUI view hierarchies."""
    code = """
    struct InvalidHierarchyView: View {
        var body: some View {
            // Invalid: Multiple root views
            Text("First")
            Text("Second")
            
            // Invalid: View inside non-View container
            VStack {
                Text("Valid")
                Button("Valid") { }
                // Invalid: View inside non-View
                if true {
                    Text("Invalid")
                }
            }
            
            // Invalid: Missing required parameters
            Image() // Missing required name parameter
            
            // Invalid: Incorrect binding
            TextField("Label", text: "Invalid") // Should be binding
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'InvalidHierarchyView'
    assert len(view['parsing_errors']) > 0
    assert any(error['type'] == 'multiple_root_views' for error in view['parsing_errors'])
    assert any(error['type'] == 'invalid_container' for error in view['parsing_errors'])
    assert any(error['type'] == 'missing_required_parameter' for error in view['parsing_errors'])
    assert any(error['type'] == 'invalid_binding' for error in view['parsing_errors'])

def test_swift_closures_and_captures(swift_parser):
    """Test parsing of Swift closures and capture lists."""
    code = """
    struct ClosureView: View {
        @State private var count = 0
        @State private var message = ""
        
        // Closure with capture list
        let increment = { [weak self] in
            guard let self = self else { return }
            self.count += 1
        }
        
        // Closure with multiple captures
        let updateMessage = { [weak self, count] in
            guard let self = self else { return }
            self.message = "Count is \(count)"
        }
        
        // Async closure
        let fetchData = { [weak self] async in
            guard let self = self else { return }
            // Simulate network call
            try? await Task.sleep(nanoseconds: 1_000_000_000)
            self.message = "Data fetched"
        }
        
        var body: some View {
            VStack {
                Text("Count: \(count)")
                Text(message)
                
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
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ClosureView'
    assert len(view['closures']) == 3
    assert all(closure['has_capture_list'] for closure in view['closures'])
    assert any(closure['is_async'] for closure in view['closures'])
    assert any(closure['has_weak_self'] for closure in view['closures'])

def test_swift_type_casting(swift_parser):
    """Test parsing of Swift type casting and type checking."""
    code = """
    struct TypeCastingView: View {
        @State private var items: [Any] = [
            "String",
            42,
            true,
            ["nested": "array"],
            User(name: "John")
        ]
        
        var body: some View {
            List(items, id: \\.self) { item in
                Group {
                    if let string = item as? String {
                        Text(string)
                    } else if let number = item as? Int {
                        Text("\(number)")
                    } else if let bool = item as? Bool {
                        Text(bool ? "True" : "False")
                    } else if let dict = item as? [String: String] {
                        Text(dict["nested"] ?? "")
                    } else if let user = item as? User {
                        Text(user.name)
                    }
                }
            }
        }
    }
    
    struct User {
        let name: String
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'TypeCastingView'
    assert len(view['type_casting']) == 5
    assert all(cast['has_type_check'] for cast in view['type_casting'])
    assert all(cast['has_optional_cast'] for cast in view['type_casting'])
    assert view['has_heterogeneous_array']

def test_swift_error_handling(swift_parser):
    """Test parsing of Swift error handling with try-catch blocks."""
    code = """
    struct ErrorHandlingView: View {
        @State private var error: Error?
        
        func fetchData() async throws {
            guard let url = URL(string: "https://api.example.com/data") else {
                throw URLError(.badURL)
            }
            
            let (data, response) = try await URLSession.shared.data(from: url)
            
            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                throw URLError(.badServerResponse)
            }
            
            // Process data
        }
        
        var body: some View {
            VStack {
                Button("Fetch Data") {
                    Task {
                        do {
                            try await fetchData()
                        } catch URLError.badURL {
                            self.error = error
                        } catch URLError.badServerResponse {
                            self.error = error
                        } catch {
                            self.error = error
                        }
                    }
                }
                
                if let error = error {
                    Text(error.localizedDescription)
                        .foregroundColor(.red)
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ErrorHandlingView'
    assert len(view['error_handling']) == 1
    assert view['error_handling'][0]['has_try_catch']
    assert view['error_handling'][0]['has_async_throws']
    assert view['error_handling'][0]['has_error_propagation']

def test_swift_optional_handling(swift_parser):
    """Test parsing of Swift optional chaining and nil coalescing."""
    code = """
    struct OptionalHandlingView: View {
        @State private var user: User?
        @State private var settings: Settings?
        
        var body: some View {
            VStack {
                Text(user?.name ?? "Guest")
                    .font(.title)
                
                if let settings = settings {
                    Text(settings.theme)
                        .foregroundColor(settings.color)
                }
                
                Button("Load User") {
                    Task {
                        // Simulate network call
                        user = await fetchUser()
                        settings = user?.preferences?.settings ?? Settings.default
                    }
                }
            }
        }
        
        func fetchUser() async -> User? {
            // Implementation
            return nil
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'OptionalHandlingView'
    assert len(view['optional_handling']) == 1
    assert view['optional_handling'][0]['has_optional_chaining']
    assert view['optional_handling'][0]['has_nil_coalescing']
    assert view['optional_handling'][0]['has_optional_binding']

def test_swift_result_builders(swift_parser):
    """Test parsing of Swift result builders in SwiftUI."""
    code = """
    struct ResultBuilderView: View {
        @State private var items = ["Item 1", "Item 2", "Item 3"]
        
        var body: some View {
            VStack {
                ForEach(items, id: \\.self) { item in
                    Text(item)
                        .padding()
                        .background(Color.blue)
                        .foregroundColor(.white)
                        .cornerRadius(8)
                }
            }
            .padding()
        }
    }
    
    @resultBuilder
    struct CustomBuilder {
        static func buildBlock(_ components: String...) -> String {
            components.joined(separator: " ")
        }
    }
    
    func customView(@CustomBuilder content: () -> String) -> String {
        content()
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ResultBuilderView'
    assert len(view['result_builders']) == 1
    assert view['result_builders'][0]['has_custom_builder']
    assert view['result_builders'][0]['has_build_block']
    assert view['result_builders'][0]['has_builder_usage']

def test_swift_property_wrapper_custom(swift_parser):
    """Test parsing of custom property wrappers in SwiftUI."""
    code = """
    @propertyWrapper
    struct Clamped<Value: Comparable> {
        var wrappedValue: Value
        let range: ClosedRange<Value>
        
        init(wrappedValue: Value, range: ClosedRange<Value>) {
            self.wrappedValue = min(max(wrappedValue, range.lowerBound), range.upperBound)
            self.range = range
        }
    }
    
    struct CustomWrapperView: View {
        @Clamped(range: 0...100) private var progress: Double = 50
        @Clamped(range: 0...255) private var red: Double = 128
        @Clamped(range: 0...255) private var green: Double = 128
        @Clamped(range: 0...255) private var blue: Double = 128
        
        var body: some View {
            VStack {
                Slider(value: $progress, in: 0...100)
                Color(red: red/255, green: green/255, blue: blue/255)
                    .frame(height: 100)
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'CustomWrapperView'
    assert len(view['property_wrappers']) == 4
    assert all(wrapper['type'] == 'Clamped' for wrapper in view['property_wrappers'])
    assert all(wrapper['has_range'] for wrapper in view['property_wrappers'])

def test_swift_complex_view_hierarchy(swift_parser):
    """Test parsing of complex nested view hierarchies in SwiftUI."""
    code = """
    struct ComplexHierarchyView: View {
        @State private var selectedTab = 0
        @State private var isShowingSheet = false
        
        var body: some View {
            TabView(selection: $selectedTab) {
                NavigationView {
                    ScrollView {
                        LazyVStack(spacing: 16) {
                            ForEach(0..<10) { index in
                                VStack(alignment: .leading) {
                                    HStack {
                                        Image(systemName: "star.fill")
                                            .foregroundColor(.yellow)
                                        Text("Item \(index)")
                                            .font(.headline)
                                    }
                                    
                                    Text("Description \(index)")
                                        .font(.subheadline)
                                        .foregroundColor(.secondary)
                                }
                                .padding()
                                .background(Color(.systemBackground))
                                .cornerRadius(12)
                                .shadow(radius: 2)
                            }
                        }
                        .padding()
                    }
                    .navigationTitle("Complex View")
                    .toolbar {
                        ToolbarItem(placement: .navigationBarTrailing) {
                            Button(action: { isShowingSheet = true }) {
                                Image(systemName: "plus")
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
            .sheet(isPresented: $isShowingSheet) {
                NavigationView {
                    AddItemView()
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ComplexHierarchyView'
    assert len(view['nested_containers']) > 0
    assert view['has_tab_view']
    assert view['has_navigation_view']
    assert view['has_scroll_view']
    assert view['has_lazy_vstack']
    assert view['has_sheet']

def test_swift_invalid_view_hierarchy(swift_parser):
    """Test parsing of invalid SwiftUI view hierarchies."""
    code = """
    struct InvalidHierarchyView: View {
        var body: some View {
            // Invalid: Multiple root views
            Text("First")
            Text("Second")
            
            // Invalid: View inside non-View container
            VStack {
                Text("Valid")
                Button("Valid") { }
                // Invalid: View inside non-View
                if true {
                    Text("Invalid")
                }
            }
            
            // Invalid: Missing required parameters
            Image() // Missing required name parameter
            
            // Invalid: Incorrect binding
            TextField("Label", text: "Invalid") // Should be binding
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'InvalidHierarchyView'
    assert len(view['parsing_errors']) > 0
    assert any(error['type'] == 'multiple_root_views' for error in view['parsing_errors'])
    assert any(error['type'] == 'invalid_container' for error in view['parsing_errors'])
    assert any(error['type'] == 'missing_required_parameter' for error in view['parsing_errors'])
    assert any(error['type'] == 'invalid_binding' for error in view['parsing_errors'])

def test_swift_closures_and_captures(swift_parser):
    """Test parsing of Swift closures and capture lists."""
    code = """
    struct ClosureView: View {
        @State private var count = 0
        @State private var message = ""
        
        // Closure with capture list
        let increment = { [weak self] in
            guard let self = self else { return }
            self.count += 1
        }
        
        // Closure with multiple captures
        let updateMessage = { [weak self, count] in
            guard let self = self else { return }
            self.message = "Count is \(count)"
        }
        
        // Async closure
        let fetchData = { [weak self] async in
            guard let self = self else { return }
            // Simulate network call
            try? await Task.sleep(nanoseconds: 1_000_000_000)
            self.message = "Data fetched"
        }
        
        var body: some View {
            VStack {
                Text("Count: \(count)")
                Text(message)
                
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
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ClosureView'
    assert len(view['closures']) == 3
    assert all(closure['has_capture_list'] for closure in view['closures'])
    assert any(closure['is_async'] for closure in view['closures'])
    assert any(closure['has_weak_self'] for closure in view['closures'])

def test_swift_type_casting(swift_parser):
    """Test parsing of Swift type casting and type checking."""
    code = """
    struct TypeCastingView: View {
        @State private var items: [Any] = [
            "String",
            42,
            true,
            ["nested": "array"],
            User(name: "John")
        ]
        
        var body: some View {
            List(items, id: \\.self) { item in
                Group {
                    if let string = item as? String {
                        Text(string)
                    } else if let number = item as? Int {
                        Text("\(number)")
                    } else if let bool = item as? Bool {
                        Text(bool ? "True" : "False")
                    } else if let dict = item as? [String: String] {
                        Text(dict["nested"] ?? "")
                    } else if let user = item as? User {
                        Text(user.name)
                    }
                }
            }
        }
    }
    
    struct User {
        let name: String
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'TypeCastingView'
    assert len(view['type_casting']) == 5
    assert all(cast['has_type_check'] for cast in view['type_casting'])
    assert all(cast['has_optional_cast'] for cast in view['type_casting'])
    assert view['has_heterogeneous_array']

def test_swift_error_handling(swift_parser):
    """Test parsing of Swift error handling with try-catch blocks."""
    code = """
    struct ErrorHandlingView: View {
        @State private var error: Error?
        
        func fetchData() async throws {
            guard let url = URL(string: "https://api.example.com/data") else {
                throw URLError(.badURL)
            }
            
            let (data, response) = try await URLSession.shared.data(from: url)
            
            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                throw URLError(.badServerResponse)
            }
            
            // Process data
        }
        
        var body: some View {
            VStack {
                Button("Fetch Data") {
                    Task {
                        do {
                            try await fetchData()
                        } catch URLError.badURL {
                            self.error = error
                        } catch URLError.badServerResponse {
                            self.error = error
                        } catch {
                            self.error = error
                        }
                    }
                }
                
                if let error = error {
                    Text(error.localizedDescription)
                        .foregroundColor(.red)
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ErrorHandlingView'
    assert len(view['error_handling']) == 1
    assert view['error_handling'][0]['has_try_catch']
    assert view['error_handling'][0]['has_async_throws']
    assert view['error_handling'][0]['has_error_propagation']

def test_swift_optional_handling(swift_parser):
    """Test parsing of Swift optional chaining and nil coalescing."""
    code = """
    struct OptionalHandlingView: View {
        @State private var user: User?
        @State private var settings: Settings?
        
        var body: some View {
            VStack {
                Text(user?.name ?? "Guest")
                    .font(.title)
                
                if let settings = settings {
                    Text(settings.theme)
                        .foregroundColor(settings.color)
                }
                
                Button("Load User") {
                    Task {
                        // Simulate network call
                        user = await fetchUser()
                        settings = user?.preferences?.settings ?? Settings.default
                    }
                }
            }
        }
        
        func fetchUser() async -> User? {
            // Implementation
            return nil
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'OptionalHandlingView'
    assert len(view['optional_handling']) == 1
    assert view['optional_handling'][0]['has_optional_chaining']
    assert view['optional_handling'][0]['has_nil_coalescing']
    assert view['optional_handling'][0]['has_optional_binding']

def test_swift_result_builders(swift_parser):
    """Test parsing of Swift result builders in SwiftUI."""
    code = """
    struct ResultBuilderView: View {
        @State private var items = ["Item 1", "Item 2", "Item 3"]
        
        var body: some View {
            VStack {
                ForEach(items, id: \\.self) { item in
                    Text(item)
                        .padding()
                        .background(Color.blue)
                        .foregroundColor(.white)
                        .cornerRadius(8)
                }
            }
            .padding()
        }
    }
    
    @resultBuilder
    struct CustomBuilder {
        static func buildBlock(_ components: String...) -> String {
            components.joined(separator: " ")
        }
    }
    
    func customView(@CustomBuilder content: () -> String) -> String {
        content()
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ResultBuilderView'
    assert len(view['result_builders']) == 1
    assert view['result_builders'][0]['has_custom_builder']
    assert view['result_builders'][0]['has_build_block']
    assert view['result_builders'][0]['has_builder_usage']

def test_swift_property_wrapper_custom(swift_parser):
    """Test parsing of custom property wrappers in SwiftUI."""
    code = """
    @propertyWrapper
    struct Clamped<Value: Comparable> {
        var wrappedValue: Value
        let range: ClosedRange<Value>
        
        init(wrappedValue: Value, range: ClosedRange<Value>) {
            self.wrappedValue = min(max(wrappedValue, range.lowerBound), range.upperBound)
            self.range = range
        }
    }
    
    struct CustomWrapperView: View {
        @Clamped(range: 0...100) private var progress: Double = 50
        @Clamped(range: 0...255) private var red: Double = 128
        @Clamped(range: 0...255) private var green: Double = 128
        @Clamped(range: 0...255) private var blue: Double = 128
        
        var body: some View {
            VStack {
                Slider(value: $progress, in: 0...100)
                Color(red: red/255, green: green/255, blue: blue/255)
                    .frame(height: 100)
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'CustomWrapperView'
    assert len(view['property_wrappers']) == 4
    assert all(wrapper['type'] == 'Clamped' for wrapper in view['property_wrappers'])
    assert all(wrapper['has_range'] for wrapper in view['property_wrappers'])

def test_swift_complex_view_hierarchy(swift_parser):
    """Test parsing of complex nested view hierarchies in SwiftUI."""
    code = """
    struct ComplexHierarchyView: View {
        @State private var selectedTab = 0
        @State private var isShowingSheet = false
        
        var body: some View {
            TabView(selection: $selectedTab) {
                NavigationView {
                    ScrollView {
                        LazyVStack(spacing: 16) {
                            ForEach(0..<10) { index in
                                VStack(alignment: .leading) {
                                    HStack {
                                        Image(systemName: "star.fill")
                                            .foregroundColor(.yellow)
                                        Text("Item \(index)")
                                            .font(.headline)
                                    }
                                    
                                    Text("Description \(index)")
                                        .font(.subheadline)
                                        .foregroundColor(.secondary)
                                }
                                .padding()
                                .background(Color(.systemBackground))
                                .cornerRadius(12)
                                .shadow(radius: 2)
                            }
                        }
                        .padding()
                    }
                    .navigationTitle("Complex View")
                    .toolbar {
                        ToolbarItem(placement: .navigationBarTrailing) {
                            Button(action: { isShowingSheet = true }) {
                                Image(systemName: "plus")
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
            .sheet(isPresented: $isShowingSheet) {
                NavigationView {
                    AddItemView()
                }
            }
        }
    }
    """
    result = swift_parser.parse(code)
    assert len(result.views) == 1
    view = result.views[0]
    assert view['name'] == 'ComplexHierarchyView'
    assert len(view['nested_containers']) > 0