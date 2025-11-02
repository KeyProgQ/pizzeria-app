import requests
from functools import partial
import math
import json

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import ListProperty, NumericProperty, StringProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import AsyncImage, Image
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Ellipse, Line
from kivy.animation import Animation
from kivy.vector import Vector

# Try to import MapView and MapMarker
try:
    from kivy_garden.mapview import MapView, MapMarker
    MAPVIEW_AVAILABLE = True
except ImportError:
    MAPVIEW_AVAILABLE = False
    print("MapView не встановлено. Використовується проста карта.")

# Ensure window background is white
Window.clearcolor = (1, 1, 1, 1)

# Base URL for API
BASE_URL = "https://slavutdevpy.pythonanywhere.com"

# Load kv
Builder.load_string('''
#:import SlideTransition kivy.uix.screenmanager.SlideTransition

<ModernRoundedButton>:
    canvas.before:
        Color:
            rgba: self.bg_color
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [self.radius]

<ModernCard>:
    canvas.before:
        Color:
            rgba: 0.8, 0.8, 0.8, 1
        RoundedRectangle:
            pos: self.pos[0]-1, self.pos[1]-1
            size: self.size[0]+2, self.size[1]+2
            radius: [self.radius]
        Color:
            rgba: 1, 1, 1, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [self.radius]

<ModernInput>:
    canvas.before:
        Color:
            rgba: 0.95, 0.95, 0.95, 1
        RoundedRectangle:
            pos: self.pos[0], self.pos[1]
            size: self.size[0], self.size[1]
            radius: [12]
        Color:
            rgba: 0.8, 0.8, 0.8, 1 if self.focus else 0.5
        Line:
            rounded_rectangle: [self.x, self.y, self.width, self.height, 12]
            width: 1.5

<ZoomControls>:
    orientation: 'vertical'
    size_hint: None, None
    size: 50, 110
    spacing: 5
    padding: 5

    ModernRoundedButton:
        text: "+"
        size_hint: 1, None
        height: 50
        bg_color: 0.3, 0.5, 0.8, 0.9
        font_size: '20sp'
        on_release: root.zoom_in()
    
    ModernRoundedButton:
        text: "-"
        size_hint: 1, None
        height: 50
        bg_color: 0.3, 0.5, 0.8, 0.9
        font_size: '20sp'
        on_release: root.zoom_out()

<MapModal>:
    BoxLayout:
        orientation: 'vertical'
        padding: 20
        spacing: 15
        
        Label:
            text: '[size=24][b]🗺️ Виберіть місце доставки[/b][/size]'
            markup: True
            size_hint_y: None
            height: 40
            color: 0.2, 0.2, 0.2, 1
        
        BoxLayout:
            size_hint_y: None
            height: 50
            spacing: 10
            
            ModernInput:
                id: search_input
                hint_text: "Пошук адреси..."
                size_hint_x: 0.7
                on_text_validate: root.search_address()
            
            ModernRoundedButton:
                text: "🔍"
                size_hint_x: 0.15
                bg_color: 0.3, 0.5, 0.8, 1
                on_release: root.search_address()
            
            ModernRoundedButton:
                text: "📍"
                size_hint_x: 0.15
                bg_color: 0.2, 0.7, 0.3, 1
                on_release: root.use_current_location()
        
        BoxLayout:
            orientation: 'vertical'
            spacing: 10
            size_hint_y: None
            height: 30
            
            Label:
                text: 'Поточні координати: {}'.format(root.selected_coords)
                size_hint_y: None
                height: 30
                color: 0.5, 0.5, 0.5, 1
                text_size: self.width, None
        
        BoxLayout:
            orientation: 'vertical'
            spacing: 10
            size_hint_y: 1
            
            RelativeLayout:
                id: map_container
                size_hint_y: 1
                
                ZoomControls:
                    id: zoom_controls
                    pos_hint: {'right': 0.95, 'top': 0.95}
        
        BoxLayout:
            size_hint_y: None
            height: 60
            spacing: 15
            
            ModernRoundedButton:
                text: "Скасувати"
                bg_color: 0.7, 0.7, 0.7, 1
                on_release: root.dismiss()
            
            ModernRoundedButton:
                text: "Підтвердити"
                bg_color: 1, 0.55, 0, 1
                on_release: root.confirm_location()

<MenuScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: [15, 10, 15, 10]
        spacing: 10
        
        # Header
        BoxLayout:
            size_hint_y: None
            height: 60
            spacing: 10
            
            Label:
                text: '[size=28][b]🍕 Піцерія[/b][/size]'
                markup: True
                color: 0.2, 0.2, 0.2, 1
                halign: 'left'
                text_size: self.width, None
            
            ModernRoundedButton:
                id: cart_button
                text: '🛒 Кошик ({})'.format(str(len(app.cart)))
                size_hint_x: None
                width: 120
                bg_color: 1, 0.55, 0, 1
                on_release: app.open_cart()
        
        # Menu items grid
        ScrollView:
            do_scroll_x: False
            GridLayout:
                id: menu_grid
                cols: 2
                spacing: 15
                padding: [0, 10, 0, 10]
                size_hint_y: None
                height: self.minimum_height

<OrderScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: 20
        spacing: 15
        
        Label:
            text: '[size=24][b]Оформлення замовлення[/b][/size]'
            markup: True
            size_hint_y: None
            height: 40
            color: 0.2, 0.2, 0.2, 1
        
        ScrollView:
            BoxLayout:
                orientation: 'vertical'
                spacing: 15
                size_hint_y: None
                height: self.minimum_height
                
                # Contact Information Section
                ModernCard:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: 250
                    padding: 15
                    spacing: 10
                    
                    Label:
                        text: '[b]👤 Контактна інформація[/b]'
                        markup: True
                        size_hint_y: None
                        height: 30
                        color: 0.2, 0.2, 0.2, 1
                    
                    BoxLayout:
                        orientation: 'horizontal'
                        spacing: 10
                        size_hint_y: None
                        height: 50
                        
                        ModernInput:
                            id: input_firstname
                            hint_text: "Ім'я"
                            size_hint_x: 0.5
                        
                        ModernInput:
                            id: input_lastname
                            hint_text: "Прізвище"
                            size_hint_x: 0.5
                    
                    ModernInput:
                        id: input_phone
                        hint_text: "📞 Номер телефону"
                        size_hint_y: None
                        height: 50
                
                # Delivery Address Section
                ModernCard:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: 180
                    padding: 15
                    spacing: 10
                    
                    Label:
                        text: '[b]📍 Адреса доставки[/b]'
                        markup: True
                        size_hint_y: None
                        height: 30
                        color: 0.2, 0.2, 0.2, 1
                    
                    ModernInput:
                        id: input_address
                        hint_text: "Введіть адресу доставки"
                        size_hint_y: None
                        height: 50
                    
                    BoxLayout:
                        size_hint_y: None
                        height: 50
                        spacing: 10
                        
                        ModernRoundedButton:
                            text: "🗺️ Вибір на карті"
                            bg_color: 0.3, 0.5, 0.8, 1
                            on_release: root.open_map_modal()
                        
                        ModernRoundedButton:
                            text: "📍 Моє місце"
                            bg_color: 0.2, 0.7, 0.3, 1
                            on_release: root.use_current_location()
                
                # Selected coordinates display
                BoxLayout:
                    id: coords_container
                    size_hint_y: None
                    height: 40
                
                # Message container for status messages
                BoxLayout:
                    id: message_container
                    size_hint_y: None
                    height: 60
                
                # Submit button
                ModernRoundedButton:
                    text: "✅ Підтвердити замовлення"
                    size_hint_y: None
                    height: 60
                    bg_color: 1, 0.55, 0, 1
                    on_release: root.submit_order()
                
                # Back button
                ModernRoundedButton:
                    text: "← Назад до меню"
                    size_hint_y: None
                    height: 50
                    bg_color: 0.7, 0.7, 0.7, 1
                    on_release: app.root.current = 'menu'
''')

# ---------- Modern UI components ----------

class ModernRoundedButton(Button):
    radius = NumericProperty(20)
    bg_color = ListProperty([1, 0.55, 0, 1])
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = [0, 0, 0, 0]
        self.color = [1, 1, 1, 1]
        self.bold = True
        self.font_size = '16sp'

    def on_press(self):
        anim = Animation(bg_color=[1, 0.45, 0, 1], d=0.1) + Animation(bg_color=[1, 0.55, 0, 1], d=0.1)
        anim.start(self)
        return super().on_press()

class ModernCard(BoxLayout):
    radius = NumericProperty(16)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = [12, 12, 12, 12]
        self.spacing = 8
        self.size_hint_y = None

class ModernInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_active = '' 
        self.background_color = [0, 0, 0, 0]
        self.multiline = False
        self.padding = [15, 10]
        self.font_size = '16sp'
        self.foreground_color = [0.2, 0.2, 0.2, 1]
        self.hint_text_color = [0.7, 0.7, 0.7, 1]
        self.cursor_color = [1, 0.55, 0, 1]

# ---------- Zoom Controls ----------

class ZoomControls(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    def zoom_in(self):
        app = App.get_running_app()
        if hasattr(app, 'current_map_modal') and app.current_map_modal:
            app.current_map_modal.zoom_in()
    
    def zoom_out(self):
        app = App.get_running_app()
        if hasattr(app, 'current_map_modal') and app.current_map_modal:
            app.current_map_modal.zoom_out()

# ---------- Enhanced Map Modal ----------

class MapModal(ModalView):
    selected_coords = StringProperty("Не вибрано")
    
    def __init__(self, callback, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (0.95, 0.9)
        self.background_color = [0, 0, 0, 0.3]
        self.overlay_color = [0, 0, 0, 0.3]
        self.callback = callback
        self.lat = 50.4501  # Київ за замовчуванням
        self.lon = 30.5234
        self.map_view = None
        self.min_zoom = 5
        self.max_zoom = 18
        self.current_zoom = 12
        self.selected_address = ""
        self.touches = {}
        self.last_touch_distance = 0
        self.is_selecting = False
        
        # Зберігаємо посилання в апп
        app = App.get_running_app()
        app.current_map_modal = self
        
        Clock.schedule_once(self._setup_map, 0.1)

    def _setup_map(self, dt):
        map_container = self.ids.map_container
        
        if MAPVIEW_AVAILABLE:
            # Створюємо карту з правильними розмірами
            self.map_view = MapView(
                zoom=self.current_zoom,
                lat=self.lat,
                lon=self.lon,
                size_hint=(1, 1),
                double_tap_zoom=True,
            )
            map_container.add_widget(self.map_view)
            
            # Додаємо маркер
            self.marker = MapMarker(lat=self.lat, lon=self.lon)
            self.map_view.add_marker(self.marker)
            
            # Обробка натискання на карту
            self.map_view.bind(
                on_touch_down=self.on_map_touch_down,
                on_touch_move=self.on_map_touch_move,
                on_touch_up=self.on_map_touch_up
            )
            
            # Оновлюємо розмір карт
            Clock.schedule_once(self._update_map_size, 0.2)
        else:
            # Запасний варіант без MapView
            fallback_layout = BoxLayout(orientation='vertical', padding=20)
            fallback_label = Label(
                text="🗺️ Мапа недоступна\n\nВстановіть kivy_garden.mapview:\npip install kivy_garden.mapview",
                color=[0.5, 0.5, 0.5, 1],
                halign='center',
                font_size='16sp'
            )
            fallback_layout.add_widget(fallback_label)
            map_container.add_widget(fallback_layout)

    def _update_map_size(self, dt):
        """Оновлює розмір мапи після її створення"""
        if self.map_view:
            self.map_view.size = self.ids.map_container.size
            self.map_view.pos = self.ids.map_container.pos

    def _get_touches_distance(self):
        """Обчислює відстань між двома тачами"""
        if len(self.touches) == 2:
            touches = list(self.touches.values())
            return Vector(touches[0].pos).distance(touches[1].pos)
        return 0

    def on_map_touch_down(self, instance, touch):
        if instance.collide_point(*touch.pos) and MAPVIEW_AVAILABLE:
            if touch.is_mouse_scrolling:
                # Обробка скролу мишею
                if touch.button == 'scrolldown':
                    self.zoom_out()
                elif touch.button == 'scrollup':
                    self.zoom_in()
                return True
            elif touch.is_double_tap:
                # Подвійний тап - зум
                self.zoom_in()
                return True
            else:
                # Звичайний тап або початок мультітачу
                self.is_selecting = True
                if len(self.touches) < 2:
                    self.touches[touch.id] = touch
                    if len(self.touches) == 2:
                        # Розпочато мультітач - обчислюємо початкову відстань
                        self.last_touch_distance = self._get_touches_distance()
                return True
        return False

    def on_map_touch_move(self, instance, touch):
        if touch.id in self.touches:
            self.touches[touch.id] = touch
            
            if len(self.touches) == 2:
                # Мультітач - обробка зуму
                self.is_selecting = False
                current_distance = self._get_touches_distance()
                if self.last_touch_distance > 0:
                    # Визначаємо напрямок зуму
                    zoom_factor = current_distance / self.last_touch_distance
                    if zoom_factor > 1.2:  # Розведення пальців
                        self.zoom_in()
                        self.last_touch_distance = current_distance
                    elif zoom_factor < 0.8:  # Зведення пальців
                        self.zoom_out()
                        self.last_touch_distance = current_distance
        return True

    def on_map_touch_up(self, instance, touch):
        if touch.id in self.touches:
            # Перевіряємо чи це був вибір точки (не мультітач і не значний рух)
            if (len(self.touches) == 1 and self.is_selecting and 
                hasattr(touch, 'dx') and hasattr(touch, 'dy') and
                abs(touch.dx) < 10 and abs(touch.dy) < 10):
                
                # Вибір точки на карті
                x, y = touch.x - instance.x, touch.y - instance.y
                try:
                    lat, lon = instance.get_latlon_at(x, y, instance.zoom)
                    
                    self.lat = lat
                    self.lon = lon
                    self.selected_coords = f"lat: {lat:.4f}, lon: {lon:.4f}"
                    
                    # Генеруємо адресу на основі координат
                    self._generate_address_from_coords(lat, lon)
                    
                    # Оновлюємо маркер
                    self.update_marker()
                    
                    # Показуємо сповіщення
                    Toast(f"📍 Координати вибрано: {lat:.4f}, {lon:.4f}").open()
                    
                except Exception as e:
                    print(f"Помилка отримання координат: {e}")
            
            del self.touches[touch.id]
            if len(self.touches) == 0:
                self.last_touch_distance = 0
                self.is_selecting = False
        return True

    def _generate_address_from_coords(self, lat, lon):
        """Генерує адресу на основі координат"""
        # Спрощена реверс геокодінг
        if 50.4 <= lat <= 50.5 and 30.4 <= lon <= 30.6:
            self.selected_address = f"м. Київ, вул. Хрещатик (координати: {lat:.4f}, {lon:.4f})"
        elif 49.8 <= lat <= 49.9 and 24.0 <= lon <= 24.1:
            self.selected_address = f"м. Львів, пл. Ринок (координати: {lat:.4f}, {lon:.4f})"
        elif 46.4 <= lat <= 46.5 and 30.7 <= lon <= 30.8:
            self.selected_address = f"м. Одеса, вул. Дерибасівська (координати: {lat:.4f}, {lon:.4f})"
        elif 49.9 <= lat <= 50.0 and 36.2 <= lon <= 36.3:
            self.selected_address = f"м. Харків, майдан Свободи (координати: {lat:.4f}, {lon:.4f})"
        else:
            self.selected_address = f"Адреса за координатами: {lat:.4f}, {lon:.4f}"

    def update_marker(self):
        """Оновлює позицію маркера"""
        if MAPVIEW_AVAILABLE and self.map_view:
            self.map_view.remove_marker(self.marker)
            self.marker = MapMarker(lat=self.lat, lon=self.lon)
            self.map_view.add_marker(self.marker)

    def zoom_in(self):
        """Збільшення масштабу"""
        if MAPVIEW_AVAILABLE and self.map_view:
            if self.map_view.zoom < self.max_zoom:
                self.map_view.zoom += 1
                self.current_zoom = self.map_view.zoom

    def zoom_out(self):
        """Зменшення масштабу"""
        if MAPVIEW_AVAILABLE and self.map_view:
            if self.map_view.zoom > self.min_zoom:
                self.map_view.zoom -= 1
                self.current_zoom = self.map_view.zoom

    def search_address(self):
        address = self.ids.search_input.text
        if not address:
            return
            
        # Спрощена імітація геокодування
        if "київ" in address.lower() or "kyiv" in address.lower():
            self.lat = 50.4501
            self.lon = 30.5234
            self.selected_address = "м. Київ, вул. Хрещатик, 1"
        elif "львів" in address.lower() or "lviv" in address.lower():
            self.lat = 49.8397
            self.lon = 24.0297
            self.selected_address = "м. Львів, пл. Ринок, 1"
        elif "одеса" in address.lower() or "odesa" in address.lower():
            self.lat = 46.4825
            self.lon = 30.7233
            self.selected_address = "м. Одеса, вул. Дерибасівська, 1"
        elif "харків" in address.lower() or "kharkiv" in address.lower():
            self.lat = 49.9935
            self.lon = 36.2304
            self.selected_address = "м. Харків, майдан Свободи, 1"
        else:
            # Випадкові координати для демонстрації
            self.lat = 50.45 + (hash(address) % 100 - 50) * 0.01
            self.lon = 30.52 + (hash(address) % 100 - 50) * 0.01
            self.selected_address = f"Адреса: {address} (координати: {self.lat:.4f}, {self.lon:.4f})"
        
        self.selected_coords = f"lat: {self.lat:.4f}, lon: {self.lon:.4f}"
        
        if MAPVIEW_AVAILABLE and self.map_view:
            self.map_view.center_on(self.lat, self.lon)
            self.update_marker()
            
        Toast(f"📍 Адресу знайдено: {self.selected_address}").open()

    def use_current_location(self):
        # Імітація GPS
        self.lat = 50.4501 + (hash(str(Clock.get_time())) % 100 - 50) * 0.001
        self.lon = 30.5234 + (hash(str(Clock.get_time())) % 100 - 50) * 0.001
        
        self.selected_coords = f"lat: {self.lat:.4f}, lon: {self.lon:.4f} (GPS)"
        self.selected_address = "м. Київ, вул. Хрещатик, 1 (визначено за GPS)"
        
        if MAPVIEW_AVAILABLE and self.map_view:
            self.map_view.center_on(self.lat, self.lon)
            self.update_marker()
            
        Toast("📍 Місцезнаходження визначено за GPS!").open()

    def confirm_location(self):
        if self.callback and self.selected_address:
            # Передаємо координати та згенеровану адресу
            self.callback(self.lat, self.lon, self.selected_coords, self.selected_address)
            Toast("✅ Місце доставки підтверджено!").open()
        else:
            Toast("❌ Будь ласка, виберіть місце на карті").open()
            return
        
        # Видаляємо посилання при закритті
        app = App.get_running_app()
        if hasattr(app, 'current_map_modal'):
            app.current_map_modal = None
        self.dismiss()

    def on_dismiss(self):
        # Видаляємо посилання при закритті
        app = App.get_running_app()
        if hasattr(app, 'current_map_modal'):
            app.current_map_modal = None

# ---------- Toast Message ----------

class Toast(ModalView):
    def __init__(self, text, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (0.8, None)
        self.height = dp(80)
        self.background_color = [0, 0, 0, 0]
        self.overlay_color = [0, 0, 0, 0]
        self.auto_dismiss = True
        
        container = BoxLayout(orientation='vertical', padding=10)
        with container.canvas.before:
            Color(0.2, 0.8, 0.2, 0.9)
            self.bg_rect = RoundedRectangle(radius=[20])
        container.bind(pos=self._update_bg, size=self._update_bg)
        
        label = Label(
            text=text,
            color=[1, 1, 1, 1],
            bold=True,
            halign='center'
        )
        container.add_widget(label)
        self.add_widget(container)
        
        self.opacity = 0
        self.open()
        anim_in = Animation(opacity=1, d=0.3)
        anim_in.start(self)
        
        Clock.schedule_once(self.dismiss_toast, 2)

    def _update_bg(self, *a):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def dismiss_toast(self, dt):
        anim_out = Animation(opacity=0, d=0.3)
        anim_out.bind(on_complete=lambda *args: self.dismiss())
        anim_out.start(self)

# ---------- Cart Modal ----------

class CartModal(ModalView):
    def __init__(self, cart_ref, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (0.95, 0.9)
        self.background_color = [0, 0, 0, 0.3]
        self.overlay_color = [0, 0, 0, 0.3]
        self.cart_ref = cart_ref

        main_container = BoxLayout(orientation="vertical", spacing=15, padding=20)
        
        with main_container.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = RoundedRectangle(radius=[25])
            
        main_container.bind(pos=self._update_bg, size=self._update_bg)

        # Header
        header = BoxLayout(size_hint_y=None, height=50)
        title = Label(
            text="[size=24][b]🛒 Ваш кошик[/b][/size]", 
            markup=True, 
            color=[0.2, 0.2, 0.2, 1]
        )
        close_btn = ModernRoundedButton(
            text="✕", 
            size_hint_x=None, 
            width=50,
            bg_color=[0.8, 0.3, 0.3, 1]
        )
        close_btn.bind(on_release=lambda x: self.dismiss())
        header.add_widget(title)
        header.add_widget(close_btn)
        main_container.add_widget(header)

        # Items
        self.grid = GridLayout(cols=1, spacing=12, size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter("height"))
        scroll = ScrollView()
        scroll.add_widget(self.grid)
        main_container.add_widget(scroll)

        # Footer
        footer = BoxLayout(size_hint_y=None, height=80, spacing=15)
        
        total_container = BoxLayout(orientation='vertical', size_hint_x=0.6)
        total_label = Label(
            text="Загальна сума:", 
            color=[0.5, 0.5, 0.5, 1],
            size_hint_y=0.5
        )
        self.total_price = Label(
            text="[size=26][b]0 ₴[/b][/size]", 
            markup=True, 
            color=[1, 0.55, 0, 1],
            size_hint_y=0.5
        )
        total_container.add_widget(total_label)
        total_container.add_widget(self.total_price)
        
        footer.add_widget(total_container)
        
        checkout_btn = ModernRoundedButton(
            text="Оформити замовлення", 
            font_size='14sp',
            bg_color=[1, 0.55, 0, 1]
        )
        checkout_btn.bind(on_release=self._checkout)
        footer.add_widget(checkout_btn)
        
        main_container.add_widget(footer)
        self.add_widget(main_container)
        
        self.populate()

    def _update_bg(self, *a):
        self.bg_rect.pos = (self.x, self.y)
        self.bg_rect.size = (self.width, self.height)

    def populate(self):
        self.grid.clear_widgets()
        total = 0
        
        if not self.cart_ref:
            empty_label = Label(
                text="[size=18]Кошик порожній[/size]\n[size=14]Додайте товари з меню[/size]",
                markup=True,
                color=[0.7, 0.7, 0.7, 1],
                halign="center"
            )
            self.grid.add_widget(empty_label)
        else:
            for i, item in enumerate(self.cart_ref):
                price = item[2]
                if isinstance(price, float):
                    formatted_price = f"{price:.2f} ₴"
                else:
                    formatted_price = f"{price} ₴"
                
                total += price
                
                item_card = BoxLayout(
                    size_hint_y=None, 
                    height=80, 
                    spacing=10,
                    padding=[10, 5]
                )
                item_card.opacity = 0
                
                # Image
                try:
                    img = AsyncImage(
                        source=f"{BASE_URL}/images/{item[0]}.png",
                        size_hint_x=None,
                        width=70
                    )
                except:
                    img = Label(text="📷", size_hint_x=None, width=70, color=[0.5, 0.5, 0.5, 1])
                
                # Info
                info_layout = BoxLayout(orientation='vertical', spacing=2)
                name_label = Label(
                    text=str(item[1]),
                    color=[0.2, 0.2, 0.2, 1],
                    halign="left",
                    size_hint_y=0.6,
                    text_size=(self.width - 150, None)
                )
                price_label = Label(
                    text=f"[b]{formatted_price}[/b]",
                    markup=True,
                    color=[1, 0.55, 0, 1],
                    halign="left",
                    size_hint_y=0.4
                )
                info_layout.add_widget(name_label)
                info_layout.add_widget(price_label)
                
                # Remove button
                remove_btn = ModernRoundedButton(
                    text="🗑️",
                    size_hint_x=None,
                    width=50,
                    bg_color=[0.95, 0.4, 0.4, 1]
                )
                remove_btn.bind(on_release=partial(self._remove_item, item, item_card))
                
                item_card.add_widget(img)
                item_card.add_widget(info_layout)
                item_card.add_widget(remove_btn)
                self.grid.add_widget(item_card)
                
                Clock.schedule_once(partial(self._animate_item, item_card), i * 0.1)
        
        if isinstance(total, float):
            formatted_total = f"{total:.2f}"
        else:
            formatted_total = f"{total}"
        
        self.total_price.text = f"[size=26][b]{formatted_total} ₴[/b][/size]"

    def _animate_item(self, item_card, dt):
        anim = Animation(opacity=1, d=0.3)
        anim.start(item_card)

    def _remove_item(self, item, item_card, *args):
        anim = Animation(opacity=0, height=0, d=0.3)
        def remove_from_list(*a):
            if item in self.cart_ref:
                self.cart_ref.remove(item)
            self.populate()
        anim.bind(on_complete=remove_from_list)
        anim.start(item_card)

    def _checkout(self, *args):
        if not self.cart_ref:
            Toast("🛒 Кошик порожній").open()
            return
        self.dismiss()
        app = App.get_running_app()
        app.root.current = "order"

# ---------- Screens ----------

class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'menu'
        self.transition = SlideTransition(duration=0.3)
        self.menu_grid = None

    def on_enter(self):
        self.opacity = 0
        anim = Animation(opacity=1, duration=0.5)
        anim.start(self)
        
        Clock.schedule_once(self._ensure_widgets, 0.1)

    def _ensure_widgets(self, dt):
        if self.menu_grid is None:
            for child in self.children:
                if hasattr(child, 'ids') and 'menu_grid' in child.ids:
                    self.menu_grid = child.ids.menu_grid
                    break
        
        if self.menu_grid is None:
            self._create_fallback_ui()
        else:
            self.populate_menu()

    def _create_fallback_ui(self):
        print("Creating fallback UI")
        main_layout = BoxLayout(orientation='vertical')
        
        header = BoxLayout(size_hint_y=None, height=60)
        header.add_widget(Label(text='🍕 Піцерія', font_size='24sp', color=[0.2, 0.2, 0.2, 1]))
        cart_btn = ModernRoundedButton(text='🛒 Кошик')
        cart_btn.bind(on_release=lambda x: App.get_running_app().open_cart())
        header.add_widget(cart_btn)
        main_layout.add_widget(header)
        
        self.menu_grid = GridLayout(cols=2, spacing=15, size_hint_y=None)
        self.menu_grid.bind(minimum_height=self.menu_grid.setter('height'))
        
        scroll = ScrollView()
        scroll.add_widget(self.menu_grid)
        main_layout.add_widget(scroll)
        
        self.clear_widgets()
        self.add_widget(main_layout)
        
        self.populate_menu()

    def populate_menu(self):
        if self.menu_grid is None:
            return
            
        self.menu_grid.clear_widgets()
        
        loading_layout = BoxLayout(orientation='vertical', spacing=20, size_hint_y=None, height=dp(100))
        loading_label = Label(
            text="Завантаження меню...",
            color=[0.5, 0.5, 0.5, 1],
            size_hint_y=None,
            height=dp(30)
        )
        
        dots = Label(
            text="●○○",
            font_size='24sp',
            color=[1, 0.55, 0, 1]
        )
        loading_layout.add_widget(loading_label)
        loading_layout.add_widget(dots)
        self.menu_grid.add_widget(loading_layout)
        
        dot_states = ["●○○", "○●○", "○○●", "○●○"]
        current_dot = 0
        def animate_dots(dt):
            nonlocal current_dot
            dots.text = dot_states[current_dot]
            current_dot = (current_dot + 1) % len(dot_states)
        
        self.dot_animation = Clock.schedule_interval(animate_dots, 0.3)
        
        Clock.schedule_once(lambda dt: self._load_menu_data(), 1)

    def _load_menu_data(self):
        if hasattr(self, 'dot_animation'):
            self.dot_animation.cancel()
            
        if self.menu_grid is None:
            return
            
        self.menu_grid.clear_widgets()
        
        try:
            response = requests.get(f"{BASE_URL}/menu", timeout=10)
            print(f"Menu response: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Received {len(data)} menu items")
                
                if not data:
                    no_data_label = Label(
                        text="Меню відсутнє",
                        color=[0.7, 0.7, 0.7, 1],
                        size_hint_y=None,
                        height=dp(50)
                    )
                    self.menu_grid.add_widget(no_data_label)
                    return

                for i, item in enumerate(data):
                    Clock.schedule_once(partial(self.add_menu_item_with_animation, item, i * 0.1), 0)
            else:
                raise Exception(f"Server error: {response.status_code}")
                
        except Exception as e:
            print(f"Error loading menu: {e}")
            self.show_error_message()

    def add_menu_item_with_animation(self, item, delay, dt):
        if self.menu_grid is None:
            return
            
        card = ModernCard()
        card.opacity = 0
        card.height = dp(280)
        
        img_container = BoxLayout(size_hint_y=0.6)
        try:
            img = AsyncImage(
                source=f"{BASE_URL}/images/{item[0]}.png",
                size_hint_y=1,
                nocache=True
            )
        except:
            placeholder = BoxLayout()
            with placeholder.canvas.before:
                Color(0.9, 0.9, 0.9, 1)
                placeholder.rect = RoundedRectangle(radius=[10])
            placeholder.bind(
                pos=lambda inst, pos: setattr(inst.rect, 'pos', pos),
                size=lambda inst, size: setattr(inst.rect, 'size', size)
            )
            img = placeholder
        
        img_container.add_widget(img)
        card.add_widget(img_container)

        price = item[2]
        if isinstance(price, float):
            formatted_price = f"{price:.2f} ₴"
        else:
            formatted_price = f"{price} ₴"

        name_label = Label(
            text=str(item[1]),
            size_hint_y=None,
            height=dp(40),
            color=[0.2, 0.2, 0.2, 1],
            halign="center",
            valign="middle",
            bold=True,
            text_size=(None, None)
        )
        card.add_widget(name_label)

        bottom_layout = BoxLayout(
            size_hint_y=None,
            height=dp(50),
            spacing=10
        )
        
        price_label = Label(
            text=f"[b]{formatted_price}[/b]",
            markup=True,
            color=[1, 0.55, 0, 1],
            text_size=(None, None)
        )
        bottom_layout.add_widget(price_label)
        
        add_btn = ModernRoundedButton(
            text="Додати",
            size_hint_x=None,
            width=dp(120),
            bg_color=[1, 0.55, 0, 1]
        )
        add_btn.bind(on_release=partial(App.get_running_app().add_to_cart, item))
        bottom_layout.add_widget(add_btn)
        
        card.add_widget(bottom_layout)
        self.menu_grid.add_widget(card)
        
        anim = Animation(opacity=1, d=0.5, t='out_back')
        anim.start(card)

    def show_error_message(self):
        if self.menu_grid is None:
            return
            
        self.menu_grid.clear_widgets()
        error_label = Label(
            text="Помилка завантаження меню",
            color=[0.8, 0.2, 0.2, 1],
            size_hint_y=None,
            height=dp(50)
        )
        retry_btn = ModernRoundedButton(
            text="Повторити",
            size_hint_y=None,
            height=dp(50),
            bg_color=[1, 0.55, 0, 1]
        )
        retry_btn.bind(on_release=lambda x: self.on_enter())
        
        error_layout = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None, height=dp(120))
        error_layout.add_widget(error_label)
        error_layout.add_widget(retry_btn)
        self.menu_grid.add_widget(error_layout)

class OrderScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'order'
        self.transition = SlideTransition(duration=0.3)
        self.selected_lat = None
        self.selected_lon = None
        self._widgets_ready = False

    def on_enter(self):
        self.opacity = 0
        anim = Animation(opacity=1, duration=0.5)
        anim.start(self)
        
        # Чекаємо, поки всі віджети будуть готові
        Clock.schedule_once(self._ensure_widgets, 0.2)

    def _ensure_widgets(self, dt):
        """Переконуємося, що всі віджети готові"""
        self._widgets_ready = True
        self.reset_form()

    def reset_form(self):
        """Скидання форми"""
        try:
            # Отримуємо посилання на поля вводу
            firstname_input = self._get_input_by_id('input_firstname')
            lastname_input = self._get_input_by_id('input_lastname')
            phone_input = self._get_input_by_id('input_phone')
            address_input = self._get_input_by_id('input_address')
            
            if firstname_input:
                firstname_input.text = ""
            if lastname_input:
                lastname_input.text = ""
            if phone_input:
                phone_input.text = ""
            if address_input:
                address_input.text = ""
            
            self.selected_lat = None
            self.selected_lon = None
            
            self.update_coords_display()
            self.clear_message()
            
        except Exception as e:
            print(f"Error resetting form: {e}")

    def _get_input_by_id(self, widget_id):
        """Безпечне отримання віджета за ID"""
        try:
            # Спосіб 1: Через root
            if hasattr(self, 'ids') and widget_id in self.ids:
                return self.ids[widget_id]
            
            # Спосіб 2: Рекурсивний пошук
            return self._find_widget_by_id(self, widget_id)
            
        except Exception as e:
            print(f"Error getting widget {widget_id}: {e}")
            return None

    def _find_widget_by_id(self, parent, widget_id):
        """Рекурсивний пошук віджета за ID"""
        if hasattr(parent, 'ids') and widget_id in parent.ids:
            return parent.ids[widget_id]
        
        for child in parent.children:
            result = self._find_widget_by_id(child, widget_id)
            if result:
                return result
        return None

    def update_coords_display(self):
        """Оновлення відображення координат"""
        coords_container = self._get_input_by_id('coords_container')
        if not coords_container:
            return
            
        coords_container.clear_widgets()
        
        if self.selected_lat and self.selected_lon:
            coords_label = Label(
                text=f"📍 Координати: {self.selected_lat:.4f}, {self.selected_lon:.4f}",
                color=[0.2, 0.6, 0.2, 1],
                size_hint_y=None,
                height=40,
                bold=True
            )
            coords_container.add_widget(coords_label)
        else:
            coords_label = Label(
                text="📍 Координати не вибрані",
                color=[0.7, 0.7, 0.7, 1],
                size_hint_y=None,
                height=40
            )
            coords_container.add_widget(coords_label)

    def open_map_modal(self):
        def on_map_selected(lat, lon, coords_text, address):
            self.selected_lat = lat
            self.selected_lon = lon
            
            # Автоматично заповнюємо поле адреси
            address_input = self._get_input_by_id('input_address')
            if address_input:
                address_input.text = address
            
            self.update_coords_display()
            Toast(f"📍 Адресу вибрано: {address}").open()
        
        map_modal = MapModal(callback=on_map_selected)
        map_modal.open()

    def use_current_location(self):
        # Імітація GPS
        self.selected_lat = 50.4501 + (hash(str(Clock.get_time())) % 100 - 50) * 0.001
        self.selected_lon = 30.5234 + (hash(str(Clock.get_time())) % 100 - 50) * 0.001
        
        address_input = self._get_input_by_id('input_address')
        if address_input:
            address_input.text = "м. Київ, вул. Хрещатик, 1 (визначено за GPS)"
        
        self.update_coords_display()
        Toast("📍 Місцезнаходження визначено за GPS!").open()

    def submit_order(self):
        """Відправка замовлення - ВИПРАВЛЕНА ВЕРСІЯ"""
        if not self._widgets_ready:
            Toast("❌ Форма ще не готова. Зачекайте.").open()
            return
            
        app = App.get_running_app()
        
        print("=== ПОЧАТОК ВІДПРАВКИ ФОРМИ ===")
        
        # Отримуємо дані з форми ПРОСТИМ способом
        firstname_input = self._get_input_by_id('input_firstname')
        lastname_input = self._get_input_by_id('input_lastname')
        phone_input = self._get_input_by_id('input_phone')
        address_input = self._get_input_by_id('input_address')
        
        # Перевіряємо, чи знайдені всі поля
        if not all([firstname_input, lastname_input, phone_input, address_input]):
            print("❌ Не всі поля знайдені!")
            print(f"Знайдені поля: firstname={firstname_input}, lastname={lastname_input}, phone={phone_input}, address={address_input}")
            Toast("❌ Помилка доступу до форми").open()
            return
        
        # Отримуємо значення
        firstname = firstname_input.text.strip()
        lastname = lastname_input.text.strip()
        phone = phone_input.text.strip()
        address = address_input.text.strip()
        
        print(f"Отримані дані: Ім'я='{firstname}', Прізвище='{lastname}', Телефон='{phone}', Адреса='{address}'")
        
        # Валідація
        validation_errors = []
        if not firstname:
            validation_errors.append("ім'я")
        if not lastname:
            validation_errors.append("прізвище") 
        if not phone:
            validation_errors.append("номер телефону")
        if not address:
            validation_errors.append("адресу")
        
        if validation_errors:
            error_msg = f"Будь ласка, заповніть {', '.join(validation_errors)}"
            print(f"Помилка валідації: {error_msg}")
            Toast(f"❌ {error_msg}").open()
            return

        if not app.cart:
            error_msg = "Кошик порожній"
            print(error_msg)
            Toast(f"❌ {error_msg}").open()
            return

        print(f"Кошик містить {len(app.cart)} товарів")

        # Підготовка даних замовлення
        try:
            order_items = []
            for item in app.cart:
                order_items.append({
                    "id": item[0], 
                    "name": item[1], 
                    "price": float(item[2])
                })
            
            order_json = json.dumps(order_items)
            print(f"JSON замовлення: {order_json}")
            
        except Exception as e:
            error_msg = f"Помилка форматування замовлення: {e}"
            print(error_msg)
            Toast(f"❌ {error_msg}").open()
            return

        # Додаємо координати до даних замовлення
        order_data = {
            "order": order_json,
            "firstname": firstname,
            "lastname": lastname,
            "phonenumber": phone,
            "adress": address
        }
        
        # Додаємо координати, якщо вони є
        if self.selected_lat and self.selected_lon:
            order_data["latitude"] = str(self.selected_lat)
            order_data["longitude"] = str(self.selected_lon)
            print(f"Додані координати: {self.selected_lat}, {self.selected_lon}")

        print(f"Дані для відправки: {order_data}")
        
        self.show_message("📤 Відправка замовлення...", loading=True)
        
        try:
            # Використовуємо правильний URL для відправки замовлення
            order_url = f"{BASE_URL}/to-order"
            print(f"Відправляємо запит на: {order_url}")
            
            # Додаємо заголовки
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            
            response = requests.post(
                order_url, 
                data=order_data,
                headers=headers,
                timeout=15
            )
            
            print(f"Статус відповіді: {response.status_code}")
            print(f"Текст відповіді: {response.text}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"Результат відповіді: {result}")
                    
                    if result.get("status") == "ok":
                        success_msg = result.get("message", "Замовлення прийнято! Дякуємо!")
                        print(f"✅ Успіх: {success_msg}")
                        Toast(f"🎉 {success_msg}").open()
                        app.cart.clear()
                        self.reset_form()  # Очищаємо форму після успішної відправки
                        Clock.schedule_once(lambda dt: setattr(app.root, 'current', 'menu'), 3.0)
                    else:
                        error_msg = result.get("message", "Помилка замовлення")
                        print(f"❌ Помилка від сервера: {error_msg}")
                        Toast(f"❌ {error_msg}").open()
                        
                except json.JSONDecodeError as e:
                    error_msg = f"Помилка обробки JSON: {e}"
                    print(f"❌ {error_msg}")
                    print(f"Вміст відповіді: {response.text}")
                    Toast("❌ Помилка обробки відповіді сервера").open()
                    
            else:
                error_msg = f"HTTP помилка: {response.status_code}"
                print(f"❌ {error_msg}")
                print(f"Вміст відповіді: {response.text}")
                Toast(f"❌ Помилка сервера: {response.status_code}").open()
                
        except requests.exceptions.Timeout:
            error_msg = "Час очікування вийшов"
            print(f"❌ {error_msg}")
            Toast("❌ Час очікування вийшов. Спробуйте ще раз.").open()
            
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Помилка з'єднання: {e}"
            print(f"❌ {error_msg}")
            Toast("❌ Помилка з'єднання. Перевірте інтернет.").open()
            
        except Exception as e:
            error_msg = f"Загальна помилка: {e}"
            print(f"❌ {error_msg}")
            Toast("❌ Помилка відправки замовлення. Спробуйте ще раз.").open()
        
        finally:
            self.clear_message()
        
        print("=== ЗАВЕРШЕННЯ ВІДПРАВКИ ФОРМИ ===")

    def show_message(self, text, error=False, loading=False, success=False):
        """Показати повідомлення"""
        message_container = self._get_input_by_id('message_container')
        if not message_container:
            return
            
        message_container.clear_widgets()
        
        if error:
            color = [0.8, 0.2, 0.2, 1]
        elif loading:
            color = [0.3, 0.5, 0.8, 1]
        elif success:
            color = [0.2, 0.6, 0.2, 1]
        else:
            color = [0.2, 0.2, 0.2, 1]
        
        message_label = Label(
            text=text,
            color=color,
            size_hint_y=None,
            height=dp(40),
            bold=True,
            opacity=0
        )
        message_container.add_widget(message_label)
        
        anim = Animation(opacity=1, d=0.5)
        anim.start(message_label)

    def clear_message(self):
        """Очистити повідомлення"""
        message_container = self._get_input_by_id('message_container')
        if message_container:
            message_container.clear_widgets()

# ---------- App ----------

class PizzaApp(App):
    cart = ListProperty([])
    current_map_modal = None
    
    def build(self):
        sm = ScreenManager(transition=SlideTransition(duration=0.3))
        sm.add_widget(MenuScreen(name="menu"))
        sm.add_widget(OrderScreen(name="order"))
        return sm

    def add_to_cart(self, item, *args):
        self.cart.append(item)
        Toast(f"✅ {item[1]} додано до кошика").open()

    def open_cart(self, *args):
        if not self.cart:
            Toast("🛒 Кошик порожній").open()
            return
        CartModal(self.cart).open()

if __name__ == "__main__":
    PizzaApp().run()