if isinstance(update, types.Message):
            # Отправляем фото и текст для нового сообщения
            await update.answer_photo(photo=photo_file, caption=text, reply_markup=keyboard, parse_mode="HTML")
        else:
            # Обновляем существующее сообщение, заменяя текст и медиа
            media = InputMediaPhoto(media=photo_file, caption=text, parse_mode="HTML")
            await update.message.edit_media(media=media, reply_markup=keyboard)