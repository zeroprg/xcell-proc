"""
Модуль для чтения данных из Excel файлов
"""

import os
import re
from typing import List, Dict, Optional
import pandas as pd
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ExcelReader:
    """Класс для чтения и обработки Excel файлов"""
    
    def __init__(self, config: Dict):
        """
        Инициализация читателя Excel
        
        Args:
            config: Словарь с настройками из конфигурационного файла.
                Требует наличия ключей `email_column`, `name_column` и
                `company_column` в `config['excel_settings']`.
        """
        self.config = config
        self.excel_settings = config.get('excel_settings', {})
        # Требуем явного указания колонок в конфиге — иначе считаем конфиг некорректным.
        try:
            self.email_column = self.excel_settings['email_column']
            self.name_column = self.excel_settings['name_column']
            self.company_column = self.excel_settings['company_column']
        except KeyError as e:
            raise ValueError(f"Missing excel_settings key: {e}")
        
    def find_excel_files(self, folder_path: str) -> List[Path]:
        """
        Найти все Excel файлы в указанной папке
        
        Args:
            folder_path: Путь к папке с Excel файлами
            
        Returns:
            Список путей к Excel файлам
        """
        folder = Path(folder_path)
        if not folder.exists():
            logger.error(f"Папка не существует: {folder_path}")
            return []
        
        excel_files = []
        for ext in ['*.xlsx', '*.xls']:
            excel_files.extend(folder.glob(ext))
        
        logger.info(f"Найдено {len(excel_files)} Excel файлов в {folder_path}")
        return excel_files
    
    def validate_email(self, email: str) -> bool:
        """
        Проверить валидность email адреса
        
        Args:
            email: Email адрес для проверки
            
        Returns:
            True если email валидный, иначе False
        """
        if not email or not isinstance(email, str):
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email.strip()))
    
    def find_email_column(self, df: pd.DataFrame) -> Optional[str]:
        """
        Автоматически найти колонку с email адресами
        
        Args:
            df: DataFrame с данными
            
        Returns:
            Название колонки с email или None
        """
        # Возможные названия колонок с email
        possible_names = ['email', 'e-mail', 'e_mail', 'mail', 'электронная почта', 'почта']
        
        for col in df.columns:
            col_lower = str(col).lower().strip()
            if col_lower in possible_names:
                return col
        
        # Попробовать найти по содержимому
        for col in df.columns:
            sample_values = df[col].dropna().head(10)
            if len(sample_values) > 0:
                valid_emails = sum(1 for val in sample_values if self.validate_email(str(val)))
                if valid_emails / len(sample_values) > 0.5:  # Если больше 50% валидные email
                    logger.info(f"Найдена колонка с email по содержимому: {col}")
                    return col
        
        return None
    
    def read_excel_file(self, file_path: Path, sheet_name: Optional[str] = None) -> List[Dict]:
        """
        Прочитать данные из Excel файла
        
        Args:
            file_path: Путь к Excel файлу
            sheet_name: Название листа (если None, читается первый лист)
            
        Returns:
            Список словарей с данными контактов
        """
        logger.info(f"Чтение файла: {file_path}")
        
        try:
            # Чтение Excel файла
            if sheet_name:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
            else:
                df = pd.read_excel(file_path)
            
            logger.info(f"Прочитано {len(df)} строк из {file_path.name}")
            
            # Найти колонку с email
            email_col = self.find_email_column(df)
            if not email_col:
                logger.error(f"Не найдена колонка с email в файле {file_path.name}")
                return []
            
            # Извлечь контакты
            contacts = []
            for idx, row in df.iterrows():
                email = str(row.get(email_col, '')).strip()
                
                if not self.validate_email(email):
                    logger.warning(f"Строка {idx + 2}: Невалидный email: {email}")
                    continue
                
                contact = {
                    'email': email,
                    'name': self._get_value(row, self.name_column),
                    'company': self._get_value(row, self.company_column),
                    'source_file': file_path.name,
                    'row_number': idx + 2
                }
                
                # Добавить все дополнительные колонки
                for col in df.columns:
                    if col not in [email_col, self.name_column, self.company_column]:
                        contact[col] = str(row.get(col, '')).strip()
                
                contacts.append(contact)
            
            logger.info(f"Извлечено {len(contacts)} валидных контактов из {file_path.name}")
            return contacts
            
        except Exception as e:
            logger.error(f"Ошибка при чтении файла {file_path}: {e}")
            return []
    
    def _get_value(self, row: pd.Series, column_name: str) -> str:
        """
        Получить значение из строки с обработкой разных вариантов названий
        
        Args:
            row: Строка DataFrame
            column_name: Название колонки
            
        Returns:
            Значение в виде строки
        """
        # Точное совпадение
        if column_name in row.index:
            value = row.get(column_name, '')
            return str(value).strip() if pd.notna(value) else ''
        
        # Регистронезависимый поиск
        for col in row.index:
            if str(col).lower() == column_name.lower():
                value = row.get(col, '')
                return str(value).strip() if pd.notna(value) else ''
        
        return ''
    
    def read_all_files(self, folder_path: str) -> List[Dict]:
        """
        Прочитать все Excel файлы из папки
        
        Args:
            folder_path: Путь к папке с Excel файлами
            
        Returns:
            Список всех контактов из всех файлов
        """
        files = self.find_excel_files(folder_path)
        all_contacts = []
        
        for file_path in files:
            contacts = self.read_excel_file(file_path)
            all_contacts.extend(contacts)
        
        # Удалить дубликаты по email
        unique_contacts = {}
        for contact in all_contacts:
            email = contact['email'].lower()
            if email not in unique_contacts:
                unique_contacts[email] = contact
            else:
                logger.debug(f"Пропущен дубликат email: {email}")
        
        result = list(unique_contacts.values())
        logger.info(f"Всего уникальных контактов: {len(result)}")
        return result
