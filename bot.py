@bot.tree.command(name="testdaily", description="Test the daily message feature (owner only)")
async def testdaily(interaction: discord.Interaction):
    if OWNER_ID == 0 or interaction.user.id != OWNER_ID:
        await interaction.response.send_message(
            "❌ Only the bot owner can use this command.",
            ephemeral=True,
        )
        return
    
    await interaction.response.defer()
    
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        await interaction.followup.send(
            f"❌ Could not find channel with ID {CHANNEL_ID}."
        )
        return
    
    try:
        # Send the daily pair
        pair = await send_daily_pair(channel)
        await interaction.followup.send(
            f"✅ Test message sent!\n"
            f"**Image:** {pair['image']}\n"
            f"**Message preview:** {pair['message'][:100]}..."
        )
        print(f"[INFO] Test daily message sent by {interaction.user}")
        
        # Send the follow-up message
        await asyncio.sleep(2)
        await channel.send(
            f"@everyone Also don't forget to say if you did or didn't do your dailys, "
            f"in the commands channel <#{COMMANDS_CHANNEL_ID}>."
        )
    except discord.Forbidden:
        await interaction.followup.send(
            "❌ Bot is missing permissions to send messages in the target channel."
        )
        print("[ERROR] Missing permissions to send messages in test channel.")
    except FileNotFoundError as e:
        await interaction.followup.send(
            f"❌ Error: Image file not found. Check your `images/` directory.\n"
            f"Details: {str(e)}"
        )
        print(f"[ERROR] Image file not found: {e}")
    except Exception as e:
        await interaction.followup.send(
            f"❌ Error sending test message: {str(e)}"
        )
        print(f"[ERROR] Failed to send test message: {e}")
