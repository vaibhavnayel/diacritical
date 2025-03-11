# Lowercase Migration for Diacritical Mappings

This document provides instructions for running the lowercase migration script, which converts all mappings in the database to lowercase format.

## Purpose

The lowercase migration ensures that:

1. All plain text and diacritic text entries in the database are converted to lowercase
2. Duplicate entries that differ only by case are merged
3. Data consistency is maintained throughout the database

## Performance Optimizations

The migration script has been optimized for high performance:

1. **Batch Processing**: Updates and deletes are processed in batches of 1000 records
2. **Direct SQL**: Uses optimized SQL queries instead of ORM operations for better performance
3. **Efficient Filtering**: Identifies uppercase mappings using database-level comparisons
4. **Minimal Memory Usage**: Processes data in chunks to reduce memory consumption
5. **Transaction Management**: Uses strategic commits to balance performance and safety

These optimizations make the migration significantly faster, especially for large datasets.

## Running the Migration

There are three ways to run the migration:

### 1. Using the standalone script

```bash
python lowercase_migration.py
```

This will:
- Find all mappings with uppercase characters
- Convert them to lowercase
- Handle potential duplicates by merging them
- Update the database with the lowercase mappings

### 2. Using the wrapper script

```bash
python run_lowercase_migration.py
```

This is a convenience wrapper around the main migration script.

### 3. Using Flask CLI

```bash
flask lowercase-migration
```

This runs the migration directly from the Flask command-line interface.

## Logging

The migration process creates detailed logs in:

- Console output (all methods)
- `lowercase_migration.log` file (when using the standalone script)

The logs include performance metrics and timing information to help you understand how long each step takes.

## Handling Duplicates

When the migration finds multiple mappings that would have the same lowercase plain text:

1. The most recently updated mapping is kept
2. Other duplicates are deleted
3. All actions are logged for review

## Verification

After running the migration, the script will verify that all mappings are now lowercase and report any that might still have uppercase characters.

## Troubleshooting

If you encounter any issues:

1. Check the log file for detailed error messages
2. Ensure your database connection is properly configured
3. Make sure you have sufficient permissions to modify the database

### Performance Issues

If the migration is still running slowly:

1. Check database server load and resources
2. Consider adjusting the batch size (default: 1000) in the script
3. Run the migration during off-peak hours

For any persistent issues, please contact the development team. 