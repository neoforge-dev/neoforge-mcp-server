import pytest
from server.code_understanding.swift_parser import parse_swift_code

def test_swiftui_complex_nested_hierarchy():
    code = r"""
    struct ComplexNestedView: View {
        @State private var selectedTab = 0
        @State private var showingSheet = false
        @State private var searchText = ""
        @State private var selectedItem: Item?
        
        var body: some View {
            TabView(selection: $selectedTab) {
                NavigationView {
                    List {
                        ForEach(items, id: \.self) { item in
                            NavigationLink(destination: DetailView(item: item)) {
                                ItemRow(item: item)
                            }
                            .swipeActions(edge: .trailing) {
                                Button(role: .destructive) {
                                    deleteItem(item)
                                } label: {
                                    Label("Delete", systemImage: "trash")
                                }
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
                NavigationView {
                    AddItemView()
                }
            }
            .sheet(item: $selectedItem) { item in
                NavigationView {
                    EditItemView(item: item)
                }
            }
        }
        
        private func deleteItem(_ item: Item) {
            // Implementation
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "ComplexNestedView"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 5
    assert all(p.property_wrapper == "@State" for p in struct.properties[:4])
    tab_view = struct.properties[4].value
    assert tab_view.type == "TabView"
    assert len(tab_view.children) == 2
    navigation_view = tab_view.children[0]
    assert navigation_view.type == "NavigationView"
    assert len(navigation_view.children) == 1
    list_view = navigation_view.children[0]
    assert list_view.type == "List"
    assert len(list_view.modifiers) == 3

def test_swiftui_advanced_state_management():
    code = r"""
    class AdvancedViewModel: ObservableObject {
        @Published var items: [Item] = []
        @Published var isLoading = false
        @Published var error: Error?
        @Published var selectedFilter: Filter = .all
        
        enum Filter {
            case all, favorites, recent
        }
        
        func fetchItems() async {
            isLoading = true
            defer { isLoading = false }
            
            do {
                let fetchedItems = try await networkService.fetchItems()
                await MainActor.run {
                    items = fetchedItems
                }
            } catch {
                await MainActor.run {
                    self.error = error
                }
            }
        }
        
        func toggleFavorite(_ item: Item) {
            if let index = items.firstIndex(where: { $0.id == item.id }) {
                items[index].isFavorite.toggle()
            }
        }
    }
    
    struct AdvancedStateView: View {
        @StateObject private var viewModel = AdvancedViewModel()
        @Environment(\.colorScheme) private var colorScheme
        @EnvironmentObject private var settings: AppSettings
        
        var filteredItems: [Item] {
            switch viewModel.selectedFilter {
            case .all:
                return viewModel.items
            case .favorites:
                return viewModel.items.filter { $0.isFavorite }
            case .recent:
                return viewModel.items.filter { $0.isRecent }
            }
        }
        
        var body: some View {
            Group {
                if viewModel.isLoading {
                    ProgressView()
                } else if let error = viewModel.error {
                    ErrorView(error: error, retryAction: {
                        Task {
                            await viewModel.fetchItems()
                        }
                    })
                } else {
                    List {
                        ForEach(filteredItems, id: \.self) { item in
                            ItemRow(item: item)
                                .swipeActions {
                                    Button(role: .destructive) {
                                        viewModel.toggleFavorite(item)
                                    } label: {
                                        Label("Toggle Favorite", systemImage: "star")
                                    }
                                }
                        }
                    }
                    .refreshable {
                        await viewModel.fetchItems()
                    }
                }
            }
            .navigationTitle("Items")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Menu {
                        Picker("Filter", selection: $viewModel.selectedFilter) {
                            Text("All").tag(AdvancedViewModel.Filter.all)
                            Text("Favorites").tag(AdvancedViewModel.Filter.favorites)
                            Text("Recent").tag(AdvancedViewModel.Filter.recent)
                        }
                    } label: {
                        Label("Filter", systemImage: "line.3.horizontal.decrease.circle")
                    }
                }
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.classes) == 1
    assert len(result.structs) == 1
    
    view_model = result.classes[0]
    assert view_model.name == "AdvancedViewModel"
    assert view_model.conforms_to == ["ObservableObject"]
    assert len(view_model.properties) == 4
    assert all(p.property_wrapper == "@Published" for p in view_model.properties)
    
    view = result.structs[0]
    assert view.name == "AdvancedStateView"
    assert view.conforms_to == ["View"]
    assert len(view.properties) == 3
    assert view.properties[0].property_wrapper == "@StateObject"
    assert view.properties[1].property_wrapper == "@Environment"
    assert view.properties[2].property_wrapper == "@EnvironmentObject"

def test_swiftui_custom_modifiers():
    code = """
    struct CardStyle: ViewModifier {
        func body(content: Content) -> some View {
            content
                .padding()
                .background(Color(.systemBackground))
                .cornerRadius(10)
                .shadow(radius: 5)
        }
    }
    
    struct GradientBackground: ViewModifier {
        let colors: [Color]
        
        func body(content: Content) -> some View {
            content
                .background(
                    LinearGradient(colors: colors, startPoint: .topLeading, endPoint: .bottomTrailing)
                )
        }
    }
    
    extension View {
        func cardStyle() -> some View {
            modifier(CardStyle())
        }
        
        func gradientBackground(_ colors: [Color]) -> some View {
            modifier(GradientBackground(colors: colors))
        }
    }
    
    struct CustomModifiersView: View {
        var body: some View {
            VStack {
                Text("Card 1")
                    .cardStyle()
                    .gradientBackground([.blue, .purple])
                
                Text("Card 2")
                    .cardStyle()
                    .gradientBackground([.green, .yellow])
            }
            .padding()
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 4
    assert len(result.extensions) == 1
    
    card_style = result.structs[0]
    assert card_style.name == "CardStyle"
    assert card_style.conforms_to == ["ViewModifier"]
    
    gradient_background = result.structs[1]
    assert gradient_background.name == "GradientBackground"
    assert gradient_background.conforms_to == ["ViewModifier"]
    
    view_extension = result.extensions[0]
    assert view_extension.type_name == "View"
    assert len(view_extension.members) == 2
    
    custom_view = result.structs[3]
    assert custom_view.name == "CustomModifiersView"
    assert custom_view.conforms_to == ["View"]
    assert len(custom_view.properties) == 1
    vstack = custom_view.properties[0].value
    assert vstack.type == "VStack"
    assert len(vstack.children) == 2
    assert all(len(child.modifiers) == 2 for child in vstack.children)

def test_swiftui_accessibility():
    code = r"""
    struct AccessibilityView: View {
        @State private var isExpanded = false
        
        var body: some View {
            VStack {
                Button {
                    withAnimation {
                        isExpanded.toggle()
                    }
                } label: {
                    HStack {
                        Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                        Text("Toggle Details")
                    }
                }
                .accessibilityLabel(isExpanded ? "Collapse details" : "Expand details")
                .accessibilityHint("Double tap to \(isExpanded ? "hide" : "show") additional information")
                
                if isExpanded {
                    VStack(alignment: .leading, spacing: 10) {
                        Text("Additional Information")
                            .font(.headline)
                            .accessibilityAddTraits(.isHeader)
                        
                        Text("This is some detailed information that appears when expanded.")
                            .accessibilityLabel("Detailed description")
                        
                        Button("Learn More") {
                            // Action
                        }
                        .accessibilityHint("Opens more information about this topic")
                    }
                    .padding()
                    .accessibilityElement(children: .contain)
                }
            }
            .accessibilityElement(children: .combine)
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "AccessibilityView"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 2
    assert struct.properties[0].name == "isExpanded"
    assert struct.properties[0].property_wrapper == "@State"
    
    vstack = struct.properties[1].value
    assert vstack.type == "VStack"
    assert len(vstack.children) == 2
    button = vstack.children[0]
    assert button.type == "Button"
    assert len(button.modifiers) == 2
    assert all(m.name == "accessibilityLabel" or m.name == "accessibilityHint" for m in button.modifiers)

def test_swiftui_error_recovery():
    code = r"""
    struct ErrorRecoveryView: View {
        @State private var items: [Item] = []
        @State private var error: Error?
        
        var body: some View {
            Group {
                if let error = error {
                    VStack {
                        Image(systemName: "exclamationmark.triangle")
                            .font(.largeTitle)
                            .foregroundColor(.red)
                        
                        Text("Something went wrong")
                            .font(.headline)
                        
                        Text(error.localizedDescription)
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                            .multilineTextAlignment(.center)
                        
                        Button("Try Again") {
                            Task {
                                await loadItems()
                            }
                        }
                        .buttonStyle(.bordered)
                    }
                    .padding()
                } else if items.isEmpty {
                    ContentUnavailableView {
                        Label("No Items", systemImage: "tray")
                    } description: {
                        Text("Items you add will appear here")
                    } actions: {
                        Button("Add Item") {
                            // Action
                        }
                    }
                } else {
                    List {
                        ForEach(items, id: \.self) { item in
                            ItemRow(item: item)
                        }
                    }
                    .refreshable {
                        await loadItems()
                    }
                }
            }
            .task {
                await loadItems()
            }
        }
        
        private func loadItems() async {
            do {
                items = try await fetchItems()
            } catch {
                self.error = error
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "ErrorRecoveryView"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 3
    assert struct.properties[0].name == "items"
    assert struct.properties[0].property_wrapper == "@State"
    assert struct.properties[1].name == "error"
    assert struct.properties[1].property_wrapper == "@State"
    
    group = struct.properties[2].value
    assert group.type == "Group"
    assert len(group.children) == 3
    assert group.children[0].type == "VStack"  # Error view
    assert group.children[1].type == "ContentUnavailableView"  # Empty state
    assert group.children[2].type == "List"  # Content view 

def test_swiftui_animations_and_transitions():
    code = """
    struct AnimatedView: View {
        @State private var isAnimating = false
        @State private var selectedTab = 0
        
        var body: some View {
            VStack {
                // Basic animation
                Circle()
                    .fill(.blue)
                    .frame(width: isAnimating ? 100 : 50)
                    .animation(.spring(response: 0.5, dampingFraction: 0.7), value: isAnimating)
                
                // Transition animation
                if isAnimating {
                    Text("Animated Text")
                        .transition(.asymmetric(
                            insertion: .scale.combined(with: .opacity),
                            removal: .slide
                        ))
                }
                
                // Tab view with custom transition
                TabView(selection: $selectedTab) {
                    Text("Tab 1")
                        .tag(0)
                    Text("Tab 2")
                        .tag(1)
                    Text("Tab 3")
                        .tag(2)
                }
                .tabViewStyle(.page)
                .animation(.easeInOut, value: selectedTab)
            }
            .onAppear {
                withAnimation(.spring()) {
                    isAnimating = true
                }
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "AnimatedView"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 3
    assert all(p.property_wrapper == "@State" for p in struct.properties[:2])
    
    vstack = struct.properties[2].value
    assert vstack.type == "VStack"
    assert len(vstack.children) == 3
    circle = vstack.children[0]
    assert circle.type == "Circle"
    assert len(circle.modifiers) == 3
    assert any(m.name == "animation" for m in circle.modifiers)

def test_swiftui_gestures_and_interactions():
    code = """
    struct GestureView: View {
        @State private var offset = CGSize.zero
        @State private var scale: CGFloat = 1.0
        @State private var rotation: Double = 0
        
        var body: some View {
            Image(systemName: "star.fill")
                .font(.system(size: 100))
                .foregroundColor(.yellow)
                .offset(offset)
                .scaleEffect(scale)
                .rotationEffect(.degrees(rotation))
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
                .gesture(
                    MagnificationGesture()
                        .onChanged { value in
                            scale = value
                        }
                        .onEnded { _ in
                            withAnimation {
                                scale = 1.0
                            }
                        }
                )
                .gesture(
                    RotationGesture()
                        .onChanged { angle in
                            rotation = angle.degrees
                        }
                        .onEnded { _ in
                            withAnimation {
                                rotation = 0
                            }
                        }
                )
                .simultaneousGesture(
                    TapGesture(count: 2)
                        .onEnded {
                            withAnimation(.spring()) {
                                scale = scale == 1.0 ? 1.5 : 1.0
                            }
                        }
                )
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "GestureView"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 4
    assert all(p.property_wrapper == "@State" for p in struct.properties)
    
    image = struct.properties[3].value
    assert image.type == "Image"
    assert len(image.modifiers) == 7
    assert any(m.name == "gesture" for m in image.modifiers)
    assert any(m.name == "simultaneousGesture" for m in image.modifiers)

def test_swiftui_advanced_layout():
    code = r"""
    struct AdvancedLayoutView: View {
        @State private var selectedTab = 0
        @State private var isExpanded = false
        
        var body: some View {
            GeometryReader { geometry in
                ScrollView {
                    VStack(spacing: 20) {
                        // Adaptive grid layout
                        LazyVGrid(columns: [
                            GridItem(.adaptive(minimum: 150, maximum: 200), spacing: 16)
                        ], spacing: 16) {
                            ForEach(0..<10) { index in
                                RoundedRectangle(cornerRadius: 12)
                                    .fill(Color.blue.opacity(0.2))
                                    .frame(height: 150)
                                    .overlay(
                                        Text("Item \(index + 1)")
                                    )
                            }
                        }
                        .padding()
                        
                        // Dynamic spacing based on screen size
                        HStack(spacing: geometry.size.width * 0.05) {
                            ForEach(0..<3) { index in
                                Circle()
                                    .fill(Color.red.opacity(0.2))
                                    .frame(width: geometry.size.width * 0.25)
                            }
                        }
                        .padding()
                        
                        // Conditional layout
                        if isExpanded {
                            VStack(alignment: .leading, spacing: 12) {
                                ForEach(0..<5) { index in
                                    HStack {
                                        Circle()
                                            .fill(Color.green.opacity(0.2))
                                            .frame(width: 40, height: 40)
                                        Text("Detail \(index + 1)")
                                        Spacer()
                                    }
                                    .padding(.horizontal)
                                }
                            }
                            .transition(.move(edge: .top).combined(with: .opacity))
                        }
                    }
                }
                .safeAreaInset(edge: .bottom) {
                    TabView(selection: $selectedTab) {
                        Text("Tab 1").tag(0)
                        Text("Tab 2").tag(1)
                        Text("Tab 3").tag(2)
                    }
                    .tabViewStyle(.page)
                    .frame(height: 50)
                    .background(.ultraThinMaterial)
                }
            }
            .ignoresSafeArea(.keyboard)
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "AdvancedLayoutView"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 3
    assert all(p.property_wrapper == "@State" for p in struct.properties)
    
    geometry_reader = struct.properties[2].value
    assert geometry_reader.type == "GeometryReader"
    assert len(geometry_reader.children) == 1
    scroll_view = geometry_reader.children[0]
    assert scroll_view.type == "ScrollView"
    assert len(scroll_view.modifiers) == 1
    assert scroll_view.modifiers[0].name == "safeAreaInset"

def test_swiftui_data_flow():
    code = r"""
    class DataFlowViewModel: ObservableObject {
        @Published var items: [Item] = []
        @Published var selectedItem: Item?
        @Published var searchText = ""
        @Published var sortOrder: SortOrder = .name
        
        enum SortOrder {
            case name, date, priority
        }
        
        var filteredAndSortedItems: [Item] {
            items
                .filter { searchText.isEmpty || $0.name.localizedCaseInsensitiveContains(searchText) }
                .sorted { item1, item2 in
                    switch sortOrder {
                    case .name:
                        return item1.name < item2.name
                    case .date:
                        return item1.date > item2.date
                    case .priority:
                        return item1.priority > item2.priority
                    }
                }
        }
    }
    
    struct DataFlowView: View {
        @StateObject private var viewModel = DataFlowViewModel()
        @Environment(\.dismiss) private var dismiss
        
        var body: some View {
            NavigationView {
                List {
                    ForEach(viewModel.filteredAndSortedItems) { item in
                        ItemRow(item: item)
                            .contentShape(Rectangle())
                            .onTapGesture {
                                viewModel.selectedItem = item
                            }
                    }
                    .onDelete { indexSet in
                        viewModel.items.remove(atOffsets: indexSet)
                    }
                    .onMove { from, to in
                        viewModel.items.move(fromOffsets: from, toOffset: to)
                    }
                }
                .searchable(text: $viewModel.searchText)
                .navigationTitle("Items")
                .toolbar {
                    ToolbarItem(placement: .navigationBarTrailing) {
                        Menu {
                            Picker("Sort", selection: $viewModel.sortOrder) {
                                Text("Name").tag(DataFlowViewModel.SortOrder.name)
                                Text("Date").tag(DataFlowViewModel.SortOrder.date)
                                Text("Priority").tag(DataFlowViewModel.SortOrder.priority)
                            }
                        } label: {
                            Label("Sort", systemImage: "arrow.up.arrow.down")
                        }
                    }
                }
                .sheet(item: $viewModel.selectedItem) { item in
                    NavigationView {
                        ItemDetailView(item: item)
                    }
                }
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.classes) == 1
    assert len(result.structs) == 1
    
    view_model = result.classes[0]
    assert view_model.name == "DataFlowViewModel"
    assert view_model.conforms_to == ["ObservableObject"]
    assert len(view_model.properties) == 4
    assert all(p.property_wrapper == "@Published" for p in view_model.properties)
    
    view = result.structs[0]
    assert view.name == "DataFlowView"
    assert view.conforms_to == ["View"]
    assert len(view.properties) == 3
    assert view.properties[0].property_wrapper == "@StateObject"
    assert view.properties[1].property_wrapper == "@Environment" 

def test_swiftui_complex_data_flow():
    code = r"""
    class ComplexDataViewModel: ObservableObject {
        @Published var items: [Item] = []
        @Published var selectedItem: Item?
        @Published var searchText = ""
        @Published var sortOrder: SortOrder = .name
        @Published var filterOptions = FilterOptions()
        
        struct FilterOptions {
            var showFavorites = false
            var dateRange: ClosedRange<Date>?
            var categories: Set<String> = []
        }
        
        var filteredAndSortedItems: [Item] {
            items
                .filter { item in
                    let matchesSearch = searchText.isEmpty || 
                        item.name.localizedCaseInsensitiveContains(searchText)
                    let matchesFavorites = !filterOptions.showFavorites || item.isFavorite
                    let matchesDate = filterOptions.dateRange == nil || 
                        filterOptions.dateRange!.contains(item.date)
                    let matchesCategories = filterOptions.categories.isEmpty || 
                        filterOptions.categories.contains(item.category)
                    return matchesSearch && matchesFavorites && matchesDate && matchesCategories
                }
                .sorted { item1, item2 in
                    switch sortOrder {
                    case .name:
                        return item1.name < item2.name
                    case .date:
                        return item1.date > item2.date
                    case .priority:
                        return item1.priority > item2.priority
                    }
                }
        }
        
        func updateFilter(_ keyPath: WritableKeyPath<FilterOptions, Bool>, value: Bool) {
            filterOptions[keyPath: keyPath] = value
        }
        
        func updateFilter(_ keyPath: WritableKeyPath<FilterOptions, Set<String>>, value: Set<String>) {
            filterOptions[keyPath: keyPath] = value
        }
    }
    
    struct ComplexDataView: View {
        @StateObject private var viewModel = ComplexDataViewModel()
        @Environment(\.dismiss) private var dismiss
        @EnvironmentObject private var settings: AppSettings
        
        var body: some View {
            NavigationView {
                VStack {
                    // Search and filter bar
                    HStack {
                        Image(systemName: "magnifyingglass")
                            .foregroundColor(.secondary)
                        TextField("Search", text: $viewModel.searchText)
                            .textFieldStyle(.roundedBorder)
                        
                        Menu {
                            Toggle("Favorites", isOn: Binding(
                                get: { viewModel.filterOptions.showFavorites },
                                set: { viewModel.updateFilter(\.showFavorites, value: $0) }
                            ))
                            
                            DateRangePicker(
                                selection: Binding(
                                    get: { viewModel.filterOptions.dateRange },
                                    set: { viewModel.filterOptions.dateRange = $0 }
                                )
                            )
                            
                            CategoryPicker(
                                selection: Binding(
                                    get: { viewModel.filterOptions.categories },
                                    set: { viewModel.updateFilter(\.categories, value: $0) }
                                )
                            )
                        } label: {
                            Image(systemName: "line.3.horizontal.decrease.circle")
                        }
                    }
                    .padding()
                    
                    // Content
                    if viewModel.filteredAndSortedItems.isEmpty {
                        ContentUnavailableView {
                            Label("No Items", systemImage: "tray")
                        } description: {
                            Text("Try adjusting your filters")
                        }
                    } else {
                        List {
                            ForEach(viewModel.filteredAndSortedItems) { item in
                                ItemRow(item: item)
                                    .contentShape(Rectangle())
                                    .onTapGesture {
                                        viewModel.selectedItem = item
                                    }
                                    .swipeActions(edge: .trailing) {
                                        Button(role: .destructive) {
                                            if let index = viewModel.items.firstIndex(where: { $0.id == item.id }) {
                                                viewModel.items.remove(at: index)
                                            }
                                        } label: {
                                            Label("Delete", systemImage: "trash")
                                        }
                                    }
                            }
                            .onDelete { indexSet in
                                viewModel.items.remove(atOffsets: indexSet)
                            }
                            .onMove { from, to in
                                viewModel.items.move(fromOffsets: from, toOffset: to)
                            }
                        }
                        .refreshable {
                            await viewModel.fetchItems()
                        }
                    }
                }
                .navigationTitle("Items")
                .toolbar {
                    ToolbarItem(placement: .navigationBarTrailing) {
                        Menu {
                            Picker("Sort", selection: $viewModel.sortOrder) {
                                Text("Name").tag(ComplexDataViewModel.SortOrder.name)
                                Text("Date").tag(ComplexDataViewModel.SortOrder.date)
                                Text("Priority").tag(ComplexDataViewModel.SortOrder.priority)
                            }
                        } label: {
                            Label("Sort", systemImage: "arrow.up.arrow.down")
                        }
                    }
                }
                .sheet(item: $viewModel.selectedItem) { item in
                    NavigationView {
                        ItemDetailView(item: item)
                    }
                }
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.classes) == 1
    assert len(result.structs) == 1
    
    view_model = result.classes[0]
    assert view_model.name == "ComplexDataViewModel"
    assert view_model.conforms_to == ["ObservableObject"]
    assert len(view_model.properties) == 5
    assert all(p.property_wrapper == "@Published" for p in view_model.properties)
    
    view = result.structs[0]
    assert view.name == "ComplexDataView"
    assert view.conforms_to == ["View"]
    assert len(view.properties) == 3
    assert view.properties[0].property_wrapper == "@StateObject"
    assert view.properties[1].property_wrapper == "@Environment"
    assert view.properties[2].property_wrapper == "@EnvironmentObject"

def test_swiftui_advanced_layout_responsiveness():
    code = r"""
    struct ResponsiveLayoutView: View {
        @Environment(\.horizontalSizeClass) private var horizontalSizeClass
        @Environment(\.verticalSizeClass) private var verticalSizeClass
        @State private var selectedTab = 0
        @State private var isExpanded = false
        
        var body: some View {
            GeometryReader { geometry in
                ScrollView {
                    VStack(spacing: 20) {
                        // Adaptive grid layout
                        LazyVGrid(
                            columns: gridColumns(for: geometry.size),
                            spacing: gridSpacing(for: geometry.size)
                        ) {
                            ForEach(0..<10) { index in
                                RoundedRectangle(cornerRadius: 12)
                                    .fill(Color.blue.opacity(0.2))
                                    .frame(height: gridItemHeight(for: geometry.size))
                                    .overlay(
                                        Text("Item \(index + 1)")
                                    )
                            }
                        }
                        .padding()
                        
                        // Dynamic spacing based on screen size
                        HStack(spacing: geometry.size.width * 0.05) {
                            ForEach(0..<3) { index in
                                Circle()
                                    .fill(Color.red.opacity(0.2))
                                    .frame(width: geometry.size.width * 0.25)
                            }
                        }
                        .padding()
                        
                        // Conditional layout based on size class
                        if horizontalSizeClass == .compact {
                            VStack(alignment: .leading, spacing: 12) {
                                ForEach(0..<5) { index in
                                    HStack {
                                        Circle()
                                            .fill(Color.green.opacity(0.2))
                                            .frame(width: 40, height: 40)
                                        Text("Detail \(index + 1)")
                                        Spacer()
                                    }
                                    .padding(.horizontal)
                                }
                            }
                        } else {
                            HStack(spacing: 20) {
                                ForEach(0..<5) { index in
                                    VStack {
                                        Circle()
                                            .fill(Color.green.opacity(0.2))
                                            .frame(width: 60, height: 60)
                                        Text("Detail \(index + 1)")
                                    }
                                }
                            }
                        }
                        
                        // Responsive text sizing
                        Text("Responsive Text")
                            .font(.system(size: min(geometry.size.width, geometry.size.height) * 0.05))
                            .multilineTextAlignment(.center)
                    }
                }
                .safeAreaInset(edge: .bottom) {
                    TabView(selection: $selectedTab) {
                        Text("Tab 1").tag(0)
                        Text("Tab 2").tag(1)
                        Text("Tab 3").tag(2)
                    }
                    .tabViewStyle(.page)
                    .frame(height: 50)
                    .background(.ultraThinMaterial)
                }
            }
            .ignoresSafeArea(.keyboard)
        }
        
        private func gridColumns(for size: CGSize) -> [GridItem] {
            let columns = Int(size.width / 150)
            return Array(repeating: GridItem(.flexible(), spacing: 16), count: max(1, columns))
        }
        
        private func gridSpacing(for size: CGSize) -> CGFloat {
            return size.width < 600 ? 8 : 16
        }
        
        private func gridItemHeight(for size: CGSize) -> CGFloat {
            return size.width < 600 ? 100 : 150
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "ResponsiveLayoutView"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 4
    assert struct.properties[0].property_wrapper == "@Environment"
    assert struct.properties[1].property_wrapper == "@Environment"
    assert all(p.property_wrapper == "@State" for p in struct.properties[2:])
    
    geometry_reader = struct.properties[3].value
    assert geometry_reader.type == "GeometryReader"
    assert len(geometry_reader.children) == 1
    scroll_view = geometry_reader.children[0]
    assert scroll_view.type == "ScrollView"
    assert len(scroll_view.modifiers) == 1
    assert scroll_view.modifiers[0].name == "safeAreaInset"

def test_swiftui_enhanced_ui_elements():
    code = r"""
    struct EnhancedUIView: View {
        @State private var text = ""
        @State private var selectedDate = Date()
        @State private var selectedColor = Color.blue
        @State private var isFocused = false
        @State private var isLoading = false
        @State private var error: Error?
        
        var body: some View {
            ScrollView {
                VStack(spacing: 20) {
                    // Enhanced TextField with validation
                    VStack(alignment: .leading) {
                        TextField("Enter text", text: $text)
                            .textFieldStyle(.roundedBorder)
                            .focused($isFocused)
                            .onChange(of: text) { newValue in
                                // Validation logic
                            }
                            .onSubmit {
                                // Submit logic
                            }
                            .submitLabel(.done)
                            .keyboardType(.default)
                            .textContentType(.name)
                        
                        if !text.isEmpty && text.count < 3 {
                            Text("Text must be at least 3 characters")
                                .font(.caption)
                                .foregroundColor(.red)
                        }
                    }
                    .padding()
                    
                    // Date picker with custom styling
                    DatePicker(
                        "Select Date",
                        selection: $selectedDate,
                        displayedComponents: [.date, .hourAndMinute]
                    )
                    .datePickerStyle(.graphical)
                    .tint(.blue)
                    .padding()
                    
                    // Color picker with custom colors
                    ColorPicker("Select Color", selection: $selectedColor)
                        .padding()
                    
                    // Async image with loading states
                    AsyncImage(url: URL(string: "https://example.com/image.jpg")) { phase in
                        switch phase {
                        case .empty:
                            ProgressView()
                                .frame(width: 200, height: 200)
                        case .success(let image):
                            image
                                .resizable()
                                .scaledToFit()
                                .frame(width: 200, height: 200)
                        case .failure(let error):
                            VStack {
                                Image(systemName: "exclamationmark.triangle")
                                    .font(.largeTitle)
                                    .foregroundColor(.red)
                                Text(error.localizedDescription)
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                            .frame(width: 200, height: 200)
                        @unknown default:
                            EmptyView()
                        }
                    }
                    .padding()
                    
                    // Canvas with custom drawing
                    Canvas { context, size in
                        let rect = CGRect(x: 0, y: 0, width: size.width, height: size.height)
                        context.fill(
                            Path(rect),
                            with: .linearGradient(
                                Gradient(colors: [.blue, .purple]),
                                startPoint: CGPoint(x: 0, y: 0),
                                endPoint: CGPoint(x: size.width, y: size.height)
                            )
                        )
                        
                        context.stroke(
                            Path(rect),
                            with: .color(.white),
                            lineWidth: 2
                        )
                    }
                    .frame(height: 200)
                    .padding()
                    
                    // Timeline view with custom schedule
                    TimelineView(.periodic(from: .now, by: 1.0)) { timeline in
                        Text("Current time: \(timeline.date.formatted())")
                            .font(.headline)
                    }
                    .padding()
                }
            }
            .navigationTitle("Enhanced UI")
            .toolbar {
                ToolbarItem(placement: .keyboard) {
                    Button("Done") {
                        isFocused = false
                    }
                }
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "EnhancedUIView"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 7
    assert all(p.property_wrapper == "@State" for p in struct.properties)
    
    scroll_view = struct.properties[6].value
    assert scroll_view.type == "ScrollView"
    assert len(scroll_view.children) == 1
    vstack = scroll_view.children[0]
    assert vstack.type == "VStack"
    assert len(vstack.children) == 6
    assert vstack.children[0].type == "VStack"  # TextField
    assert vstack.children[1].type == "DatePicker"  # Date picker
    assert vstack.children[2].type == "ColorPicker"  # Color picker
    assert vstack.children[3].type == "AsyncImage"  # Async image
    assert vstack.children[4].type == "Canvas"  # Canvas
    assert vstack.children[5].type == "TimelineView"  # Timeline view 

def test_swiftui_advanced_combine_integration():
    code = """
    class CombineViewModel: ObservableObject {
        @Published var searchText = ""
        @Published var searchResults: [Item] = []
        @Published var isLoading = false
        @Published var error: Error?
        
        private var cancellables = Set<AnyCancellable>()
        private let searchSubject = PassthroughSubject<String, Never>()
        
        init() {
            setupSearchPipeline()
        }
        
        private func setupSearchPipeline() {
            searchSubject
                .debounce(for: .milliseconds(300), scheduler: RunLoop.main)
                .removeDuplicates()
                .filter { !$0.isEmpty }
                .handleEvents(receiveOutput: { [weak self] _ in
                    self?.isLoading = true
                })
                .asyncMap { [weak self] query in
                    try await self?.performSearch(query: query)
                }
                .receive(on: DispatchQueue.main)
                .sink { [weak self] completion in
                    self?.isLoading = false
                    if case .failure(let error) = completion {
                        self?.error = error
                    }
                } receiveValue: { [weak self] results in
                    self?.searchResults = results
                    self?.error = nil
                }
                .store(in: &cancellables)
        }
        
        func search(_ query: String) {
            searchSubject.send(query)
        }
        
        private func performSearch(query: String) async throws -> [Item] {
            // Implementation
            return []
        }
    }
    
    struct CombineIntegrationView: View {
        @StateObject private var viewModel = CombineViewModel()
        @State private var selectedItem: Item?
        
        var body: some View {
            NavigationView {
                VStack {
                    // Search bar with Combine integration
                    SearchBar(text: $viewModel.searchText)
                        .onChange(of: viewModel.searchText) { newValue in
                            viewModel.search(newValue)
                        }
                    
                    if viewModel.isLoading {
                        ProgressView()
                    } else if let error = viewModel.error {
                        ErrorView(error: error)
                    } else {
                        List(viewModel.searchResults) { item in
                            ItemRow(item: item)
                                .onTapGesture {
                                    selectedItem = item
                                }
                        }
                    }
                }
                .navigationTitle("Search")
                .sheet(item: $selectedItem) { item in
                    ItemDetailView(item: item)
                }
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.classes) == 1
    assert len(result.structs) == 1
    
    view_model = result.classes[0]
    assert view_model.name == "CombineViewModel"
    assert view_model.conforms_to == ["ObservableObject"]
    assert len(view_model.properties) == 4
    assert all(p.property_wrapper == "@Published" for p in view_model.properties)
    
    view = result.structs[0]
    assert view.name == "CombineIntegrationView"
    assert view.conforms_to == ["View"]
    assert len(view.properties) == 2
    assert view.properties[0].property_wrapper == "@StateObject"
    assert view.properties[1].property_wrapper == "@State"

def test_swiftui_advanced_localization():
    code = r"""
    struct LocalizedView: View {
        @Environment(\.locale) private var locale
        @Environment(\.layoutDirection) private var layoutDirection
        @State private var selectedDate = Date()
        @State private var amount: Double = 0
        
        var body: some View {
            ScrollView {
                VStack(spacing: 20) {
                    // Localized text with dynamic type
                    Text("welcome_message", bundle: .main)
                        .font(.title)
                        .dynamicTypeSize(.xSmall...(.accessibility5))
                    
                    // RTL-aware layout
                    HStack {
                        Image(systemName: "star.fill")
                        Text("rating")
                    }
                    .environment(\.layoutDirection, layoutDirection)
                    
                    // Localized date formatting
                    DatePicker(
                        "select_date",
                        selection: $selectedDate,
                        displayedComponents: [.date]
                    )
                    .datePickerStyle(.graphical)
                    .environment(\.locale, locale)
                    
                    // Localized number formatting
                    HStack {
                        Text("amount_label")
                        Text(amount, format: .currency(code: locale.currency?.identifier ?? "USD"))
                    }
                    
                    // Localized list
                    List {
                        ForEach(0..<5) { index in
                            HStack {
                                Text("item_\(index)")
                                Spacer()
                                Text("\(index + 1)")
                            }
                        }
                    }
                    .environment(\.locale, locale)
                }
                .padding()
            }
            .navigationTitle("localized_title")
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "LocalizedView"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 4
    assert struct.properties[0].property_wrapper == "@Environment"
    assert struct.properties[1].property_wrapper == "@Environment"
    assert all(p.property_wrapper == "@State" for p in struct.properties[2:])
    
    scroll_view = struct.properties[3].value
    assert scroll_view.type == "ScrollView"
    assert len(scroll_view.children) == 1
    vstack = scroll_view.children[0]
    assert vstack.type == "VStack"
    assert len(vstack.children) == 5
    assert vstack.children[0].type == "Text"  # Localized text
    assert vstack.children[1].type == "HStack"  # RTL layout
    assert vstack.children[2].type == "DatePicker"  # Localized date
    assert vstack.children[3].type == "HStack"  # Localized number
    assert vstack.children[4].type == "List"  # Localized list

def test_swiftui_advanced_performance():
    code = """
    struct PerformanceOptimizedView: View {
        @StateObject private var viewModel = PerformanceViewModel()
        @State private var selectedTab = 0
        
        var body: some View {
            TabView(selection: $selectedTab) {
                // Lazy loading list with pagination
                LazyList {
                    ForEach(viewModel.items) { item in
                        ItemRow(item: item)
                            .id(item.id)
                            .task {
                                if item.id == viewModel.items.last?.id {
                                    await viewModel.loadMoreItems()
                                }
                            }
                    }
                }
                .tabItem {
                    Label("Items", systemImage: "list.bullet")
                }
                .tag(0)
                
                // Optimized grid with prefetching
                LazyGrid {
                    ForEach(viewModel.gridItems) { item in
                        GridItemView(item: item)
                            .task {
                                if item.id == viewModel.gridItems.last?.id {
                                    await viewModel.loadMoreGridItems()
                                }
                            }
                    }
                }
                .tabItem {
                    Label("Grid", systemImage: "square.grid.2x2")
                }
                .tag(1)
            }
            .task {
                await viewModel.loadInitialData()
            }
        }
    }
    
    // Optimized view model with memory management
    class PerformanceViewModel: ObservableObject {
        @Published private(set) var items: [Item] = []
        @Published private(set) var gridItems: [GridItem] = []
        @Published private(set) var isLoading = false
        @Published private(set) var error: Error?
        
        private var currentPage = 1
        private var hasMoreItems = true
        private let pageSize = 20
        
        func loadInitialData() async {
            guard !isLoading else { return }
            isLoading = true
            defer { isLoading = false }
            
            do {
                let initialItems = try await fetchItems(page: 1, pageSize: pageSize)
                await MainActor.run {
                    items = initialItems
                    hasMoreItems = initialItems.count == pageSize
                }
            } catch {
                await MainActor.run {
                    self.error = error
                }
            }
        }
        
        func loadMoreItems() async {
            guard !isLoading && hasMoreItems else { return }
            isLoading = true
            defer { isLoading = false }
            
            do {
                let nextPage = currentPage + 1
                let newItems = try await fetchItems(page: nextPage, pageSize: pageSize)
                await MainActor.run {
                    items.append(contentsOf: newItems)
                    currentPage = nextPage
                    hasMoreItems = newItems.count == pageSize
                }
            } catch {
                await MainActor.run {
                    self.error = error
                }
            }
        }
        
        private func fetchItems(page: Int, pageSize: Int) async throws -> [Item] {
            // Implementation
            return []
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.classes) == 1
    assert len(result.structs) == 1
    
    view_model = result.classes[0]
    assert view_model.name == "PerformanceViewModel"
    assert view_model.conforms_to == ["ObservableObject"]
    assert len(view_model.properties) == 4
    assert all(p.property_wrapper == "@Published" for p in view_model.properties)
    
    view = result.structs[0]
    assert view.name == "PerformanceOptimizedView"
    assert view.conforms_to == ["View"]
    assert len(view.properties) == 2
    assert view.properties[0].property_wrapper == "@StateObject"
    assert view.properties[1].property_wrapper == "@State"
    
    tab_view = view.properties[1].value
    assert tab_view.type == "TabView"
    assert len(tab_view.children) == 2
    assert tab_view.children[0].type == "LazyList"  # Lazy loading list
    assert tab_view.children[1].type == "LazyGrid"  # Optimized grid 

def test_swiftui_advanced_data_management():
    code = r"""
    class ComplexDataViewModel: ObservableObject {
        @Published var items: [Item] = []
        @Published var selectedItem: Item?
        @Published var sortOrder: SortOrder = .name
        @Published var filterOptions = FilterOptions()
        @Published var isLoading = false
        
        enum SortOrder {
            case name, date, priority
        }
        
        struct FilterOptions {
            var showFavorites = false
            var dateRange: DateRange?
            var categories: Set<Category> = []
        }
        
        var filteredAndSortedItems: [Item] {
            // Implementation
            return []
        }
        
        func fetchItems() async {
            // Implementation
        }
        
        func updateFilter(_ keyPath: WritableKeyPath<FilterOptions, Bool>, value: Bool) {
            // Implementation
        }
        
        func updateFilter(_ keyPath: WritableKeyPath<FilterOptions, Set<Category>>, value: Set<Category>) {
            // Implementation
        }
    }
    
    struct ComplexDataView: View {
        @StateObject private var viewModel = ComplexDataViewModel()
        @Environment(\.colorScheme) private var colorScheme
        @EnvironmentObject private var settings: AppSettings
        
        var body: some View {
            NavigationView {
                VStack {
                    // Filters
                    HStack {
                        Menu {
                            Toggle("Favorites", isOn: Binding(
                                get: { viewModel.filterOptions.showFavorites },
                                set: { viewModel.updateFilter(\.showFavorites, value: $0) }
                            ))
                            
                            DateRangePicker(
                                selection: Binding(
                                    get: { viewModel.filterOptions.dateRange },
                                    set: { viewModel.filterOptions.dateRange = $0 }
                                )
                            )
                            
                            CategoryPicker(
                                selection: Binding(
                                    get: { viewModel.filterOptions.categories },
                                    set: { viewModel.updateFilter(\.categories, value: $0) }
                                )
                            )
                        } label: {
                            Image(systemName: "line.3.horizontal.decrease.circle")
                        }
                    }
                    .padding()
                    
                    // Content
                    if viewModel.filteredAndSortedItems.isEmpty {
                        ContentUnavailableView {
                            Label("No Items", systemImage: "tray")
                        } description: {
                            Text("Try adjusting your filters")
                        }
                    } else {
                        List {
                            ForEach(viewModel.filteredAndSortedItems) { item in
                                ItemRow(item: item)
                                    .contentShape(Rectangle())
                                    .onTapGesture {
                                        viewModel.selectedItem = item
                                    }
                                    .swipeActions(edge: .trailing) {
                                        Button(role: .destructive) {
                                            if let index = viewModel.items.firstIndex(where: { $0.id == item.id }) {
                                                viewModel.items.remove(at: index)
                                            }
                                        } label: {
                                            Label("Delete", systemImage: "trash")
                                        }
                                    }
                            }
                            .onDelete { indexSet in
                                viewModel.items.remove(atOffsets: indexSet)
                            }
                            .onMove { from, to in
                                viewModel.items.move(fromOffsets: from, toOffset: to)
                            }
                        }
                        .refreshable {
                            await viewModel.fetchItems()
                        }
                    }
                }
                .navigationTitle("Items")
                .toolbar {
                    ToolbarItem(placement: .navigationBarTrailing) {
                        Menu {
                            Picker("Sort", selection: $viewModel.sortOrder) {
                                Text("Name").tag(ComplexDataViewModel.SortOrder.name)
                                Text("Date").tag(ComplexDataViewModel.SortOrder.date)
                                Text("Priority").tag(ComplexDataViewModel.SortOrder.priority)
                            }
                        } label: {
                            Label("Sort", systemImage: "arrow.up.arrow.down")
                        }
                    }
                }
                .sheet(item: $viewModel.selectedItem) { item in
                    NavigationView {
                        ItemDetailView(item: item)
                    }
                }
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.classes) == 1
    assert len(result.structs) == 1
    
    view_model = result.classes[0]
    assert view_model.name == "ComplexDataViewModel"
    assert view_model.conforms_to == ["ObservableObject"]
    assert len(view_model.properties) == 5
    assert all(p.property_wrapper == "@Published" for p in view_model.properties)
    
    view = result.structs[0]
    assert view.name == "ComplexDataView"
    assert view.conforms_to == ["View"]
    assert len(view.properties) == 3
    assert view.properties[0].property_wrapper == "@StateObject"
    assert view.properties[1].property_wrapper == "@Environment"
    assert view.properties[2].property_wrapper == "@EnvironmentObject"

def test_swiftui_complex_layout():
    code = r"""
    struct ComplexLayoutView: View {
        @Environment(\.horizontalSizeClass) private var horizontalSizeClass
        @Environment(\.verticalSizeClass) private var verticalSizeClass
        @State private var selectedTab = 0
        @State private var isExpanded = false
        @State private var scrollOffset: CGFloat = 0
        
        var body: some View {
            GeometryReader { geometry in
                ScrollView {
                    VStack(spacing: 20) {
                        // Adaptive grid layout
                        LazyVGrid(
                            columns: gridColumns(for: geometry.size),
                            spacing: gridSpacing(for: geometry.size)
                        ) {
                            ForEach(0..<10) { index in
                                RoundedRectangle(cornerRadius: 12)
                                    .fill(Color.blue.opacity(0.2))
                                    .frame(height: gridItemHeight(for: geometry.size))
                                    .overlay(
                                        Text("Item \(index + 1)")
                                    )
                            }
                        }
                        .padding()
                        
                        // Dynamic spacing based on screen size
                        HStack(spacing: geometry.size.width * 0.05) {
                            ForEach(0..<3) { index in
                                Circle()
                                    .fill(Color.red.opacity(0.2))
                                    .frame(width: geometry.size.width * 0.25)
                            }
                        }
                        .padding()
                        
                        // Conditional layout based on size class
                        if horizontalSizeClass == .compact {
                            VStack(alignment: .leading, spacing: 12) {
                                ForEach(0..<5) { index in
                                    HStack {
                                        Circle()
                                            .fill(Color.green.opacity(0.2))
                                            .frame(width: 40, height: 40)
                                        Text("Detail \(index + 1)")
                                        Spacer()
                                    }
                                    .padding(.horizontal)
                                }
                            }
                        } else {
                            HStack(spacing: 20) {
                                ForEach(0..<5) { index in
                                    VStack {
                                        Circle()
                                            .fill(Color.green.opacity(0.2))
                                            .frame(width: 60, height: 60)
                                        Text("Detail \(index + 1)")
                                    }
                                }
                            }
                        }
                        
                        // Responsive text sizing
                        Text("Responsive Text")
                            .font(.system(size: min(geometry.size.width, geometry.size.height) * 0.05))
                            .multilineTextAlignment(.center)
                    }
                }
                .safeAreaInset(edge: .bottom) {
                    TabView(selection: $selectedTab) {
                        Text("Tab 1").tag(0)
                        Text("Tab 2").tag(1)
                        Text("Tab 3").tag(2)
                    }
                    .tabViewStyle(.page)
                    .frame(height: 50)
                    .background(.ultraThinMaterial)
                }
            }
            .ignoresSafeArea(.keyboard)
        }
        
        private func gridColumns(for size: CGSize) -> [GridItem] {
            let columns = Int(size.width / 150)
            return Array(repeating: GridItem(.flexible(), spacing: 16), count: max(1, columns))
        }
        
        private func gridSpacing(for size: CGSize) -> CGFloat {
            return size.width < 600 ? 8 : 16
        }
        
        private func gridItemHeight(for size: CGSize) -> CGFloat {
            return size.width < 600 ? 100 : 150
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "ComplexLayoutView"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 4
    assert struct.properties[0].property_wrapper == "@Environment"
    assert struct.properties[1].property_wrapper == "@Environment"
    assert all(p.property_wrapper == "@State" for p in struct.properties[2:])
    
    geometry_reader = struct.properties[3].value
    assert geometry_reader.type == "GeometryReader"
    assert len(geometry_reader.children) == 1
    scroll_view = geometry_reader.children[0]
    assert scroll_view.type == "ScrollView"
    assert len(scroll_view.modifiers) == 1
    assert scroll_view.modifiers[0].name == "safeAreaInset"

def test_swiftui_enhanced_ui_elements():
    code = r"""
    struct EnhancedUIView: View {
        @State private var text = ""
        @State private var selectedDate = Date()
        @State private var selectedColor = Color.blue
        @State private var isFocused = false
        @State private var isLoading = false
        @State private var error: Error?
        
        var body: some View {
            ScrollView {
                VStack(spacing: 20) {
                    // Enhanced TextField with validation
                    VStack(alignment: .leading) {
                        TextField("Enter text", text: $text)
                            .textFieldStyle(.roundedBorder)
                            .focused($isFocused)
                            .onChange(of: text) { newValue in
                                // Validation logic
                            }
                            .onSubmit {
                                // Submit logic
                            }
                            .submitLabel(.done)
                            .keyboardType(.default)
                            .textContentType(.name)
                        
                        if !text.isEmpty && text.count < 3 {
                            Text("Text must be at least 3 characters")
                                .font(.caption)
                                .foregroundColor(.red)
                        }
                    }
                    .padding()
                    
                    // Date picker with custom styling
                    DatePicker(
                        "Select Date",
                        selection: $selectedDate,
                        displayedComponents: [.date, .hourAndMinute]
                    )
                    .datePickerStyle(.graphical)
                    .tint(.blue)
                    .padding()
                    
                    // Color picker with custom colors
                    ColorPicker("Select Color", selection: $selectedColor)
                        .padding()
                    
                    // Async image with loading states
                    AsyncImage(url: URL(string: "https://example.com/image.jpg")) { phase in
                        switch phase {
                        case .empty:
                            ProgressView()
                                .frame(width: 200, height: 200)
                        case .success(let image):
                            image
                                .resizable()
                                .scaledToFit()
                                .frame(width: 200, height: 200)
                        case .failure(let error):
                            VStack {
                                Image(systemName: "exclamationmark.triangle")
                                    .font(.largeTitle)
                                    .foregroundColor(.red)
                                Text(error.localizedDescription)
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                            .frame(width: 200, height: 200)
                        @unknown default:
                            EmptyView()
                        }
                    }
                    .padding()
                    
                    // Canvas with custom drawing
                    Canvas { context, size in
                        let rect = CGRect(x: 0, y: 0, width: size.width, height: size.height)
                        context.fill(
                            Path(rect),
                            with: .linearGradient(
                                Gradient(colors: [.blue, .purple]),
                                startPoint: CGPoint(x: 0, y: 0),
                                endPoint: CGPoint(x: size.width, y: size.height)
                            )
                        )
                        
                        context.stroke(
                            Path(rect),
                            with: .color(.white),
                            lineWidth: 2
                        )
                    }
                    .frame(height: 200)
                    .padding()
                    
                    // Timeline view with custom schedule
                    TimelineView(.periodic(from: .now, by: 1.0)) { timeline in
                        Text("Current time: \(timeline.date.formatted())")
                            .font(.headline)
                    }
                    .padding()
                }
            }
            .navigationTitle("Enhanced UI")
            .toolbar {
                ToolbarItem(placement: .keyboard) {
                    Button("Done") {
                        isFocused = false
                    }
                }
            }
        }
    }
    """
    result = parse_swift_code(code)
    assert len(result.structs) == 1
    struct = result.structs[0]
    assert struct.name == "EnhancedUIView"
    assert struct.conforms_to == ["View"]
    assert len(struct.properties) == 7
    assert all(p.property_wrapper == "@State" for p in struct.properties)
    
    scroll_view = struct.properties[6].value
    assert scroll_view.type == "ScrollView"
    assert len(scroll_view.children) == 1
    vstack = scroll_view.children[0]
    assert vstack.type == "VStack"
    assert len(vstack.children) == 6
    assert vstack.children[0].type == "VStack"  # TextField
    assert vstack.children[1].type == "DatePicker"  # Date picker
    assert vstack.children[2].type == "ColorPicker"  # Color picker
    assert vstack.children[3].type == "AsyncImage"  # Async image
    assert vstack.children[4].type == "Canvas"  # Canvas
    assert vstack.children[5].type == "TimelineView"  # Timeline view 